import sys
sys.path.insert(0, '../')
import re
import os
import datetime
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from lib.database import db_execute, db_query


def parse_socialblade_date(date_str):
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    
    try:
        date_obj = datetime.datetime.strptime(date_str, "%b %d, %Y")
        return date_obj, date_obj.strftime("%Y-%m-%d")
    except ValueError:
        try:
            date_obj = datetime.datetime.strptime(date_str, "%B %d, %Y")
            return date_obj, date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None, date_str


def parse_count(text):
    return int(text.replace(",", ""))


def extract_socialblade_profile_data(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')
    profile_data = {}
    
    info_wrap = soup.find('div', id='YouTubeUserTopInfoWrap')
    if not info_wrap:
        return None
    
    avatar = info_wrap.find('img', id='YouTubeUserTopInfoAvatar')
    if avatar:
        profile_data['avatar_url'] = avatar.get('src')
    
    username_element = info_wrap.find('h2')
    if username_element:
        profile_data['username'] = username_element.contents[0].strip()
        handle_element = username_element.find('a')
        if handle_element:
            profile_data['handle'] = handle_element.text.strip()
    
    info_blocks = info_wrap.find_all('div', class_='YouTubeUserTopInfo')
    for block in info_blocks:
        label = block.find('span', class_='YouTubeUserTopLight')
        if not label:
            continue
            
        value = block.find('span', style='font-weight: bold;')
        if not value:
            continue
            
        label_text = label.text.strip().lower()
        value_text = value.text.strip()
        
        if 'followers' in label_text:
            profile_data['followers'] = parse_count(value_text)
        elif 'following' in label_text:
            profile_data['following'] = parse_count(value_text)
        elif 'tweets' in label_text:
            profile_data['tweets'] = parse_count(value_text)
        elif 'user created' in label_text:
            profile_data['created_at'], _ = parse_socialblade_date(value_text)
    
    return profile_data


def get_authors_to_fetch():
    authors_query = "SELECT DISTINCT author FROM twitter_forecast WHERE author_followers_count IS NULL"
    return [row["author"] for row in db_query(authors_query)]


def create_profile_update_query(profile, author):
    set_clauses = []
    values = []
    
    # Only include fields that exist in the database
    profile_field_mapping = {
        'followers': 'author_followers_count',
        'following': 'author_following_count',
        'tweets': 'author_tweet_count',
        'created_at': 'author_created_at'
    }
    
    for profile_field, db_field in profile_field_mapping.items():
        if profile.get(profile_field) is not None:
            set_clauses.append(f"{db_field} = %s")
            values.append(profile[profile_field])
    
    if not set_clauses:
        return None, None
    
    values.append(author)
    update_query = f"UPDATE twitter_forecast SET {', '.join(set_clauses)} WHERE author = %s"
    
    return update_query, values


async def check_if_profile_exists(page):
    page_content = await page.content()
    return "does not exist on Twitter" not in page_content


async def fetch_profile_for_author(page, author):
    try:
        print(f"Fetching profile for {author}")
        await page.goto(f"https://socialblade.com/twitter/user/{author}")
        
        # Check if profile exists on Twitter
        if not await check_if_profile_exists(page):
            print(f"Profile {author} does not exist on Twitter")
            return None
        
        # Wait for the profile data element to load
        try:
            await page.wait_for_selector('div[id="YouTubeUserTopInfoWrap"]', state="visible", timeout=30000)
            return extract_socialblade_profile_data(await page.content())
        except Exception as e:
            print(f"Selector timeout for {author}: {str(e)}")
            return None
            
    except Exception as e:
        print(f"Error waiting for selector for {author}: {str(e)}")
        return None


async def update_author_profile(page, author):
    try:
        profile = await fetch_profile_for_author(page, author)
        
        if profile:
            print(f"Found profile data for {author}: {profile}")
            update_query, values = create_profile_update_query(profile, author)
            
            if update_query:
                db_execute(update_query, values)
                print(f"Updated database for {author}")
        else:
            print(f"No profile data found for {author}")
            
            # For non-existent profiles, we can log but not update since there's no author_exists column
            if not await check_if_profile_exists(page):
                print(f"Profile {author} doesn't exist (but can't mark in DB - no 'author_exists' column)")
            
        await page.wait_for_timeout(2000)
        
    except Exception as e:
        print(f"Error processing {author}: {str(e)}")


async def process_authors_chunk(context, authors_chunk):
    """Process a chunk of authors using a dedicated page."""
    page = await context.new_page()
    try:
        for author in authors_chunk:
            await update_author_profile(page, author)
    finally:
        await page.close()


async def main():
    MAX_CONCURRENT_TASKS = 5
    
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        
        browser_context_options = {
            "proxy": {
                "server": f"http://{os.getenv('PROXY_HOST')}:{os.getenv('PROXY_PORT')}",
                "username": os.getenv("PROXY_USERNAME"),
                "password": os.getenv("PROXY_PASSWORD")
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        
        print("Launching browser...")
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(**browser_context_options)
        print("Browser launched successfully")
        
        authors = get_authors_to_fetch()
        print(f"Fetching profiles for {len(authors)} authors with {MAX_CONCURRENT_TASKS} parallel tasks")
        
        # Process authors in chunks
        while authors:
            # Create tasks for up to MAX_CONCURRENT_TASKS authors at once
            tasks = []
            
            for _ in range(MAX_CONCURRENT_TASKS):
                if not authors:
                    break
                
                # Take a chunk of authors for each task (1 author per task)
                author = authors.pop(0)
                task = process_authors_chunk(context, [author])
                tasks.append(task)
            
            # Run tasks concurrently
            await asyncio.gather(*tasks)
            
    except Exception as e:
        print(f"Fatal error in main: {str(e)}")
    finally:
        if browser:
            print("Closing browser...")
            await browser.close()
        if playwright:
            print("Closing playwright...")
            await playwright.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())