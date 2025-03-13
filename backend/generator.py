import dotenv
dotenv.load_dotenv()
import os
from openai import OpenAI
from bs4 import BeautifulSoup


class TweetGenerator:
    def __init__(self, provider: str = "openai"):
        if provider == "openai":
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
            self.model = "gpt-4o"
        elif provider == "deepseek":
            self.client = OpenAI(
                base_url="https://api.deepseek.com",
                api_key=os.getenv("DEEPSEEK_API_KEY")
            )
            # self.model = "deepseek-reasoner"
            self.model = "deepseek-chat"

    def generate_tweets(self, tweets: list[str], custom_instructions: str = "") -> list[str]:
        tweets_str = "\n".join([f"<tweet>{tweet}</tweet>" for tweet in tweets])
        custom_inst_prompt = Ref.custom_instructions.format(custom_instructions=custom_instructions) if custom_instructions else ""
        system_prompt = Ref.system_prompt.format(custom_instructions=custom_inst_prompt)
        tweet_prompt = Ref.tweet_prompt.format(tweets=tweets_str)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": tweet_prompt}
            ],
            max_completion_tokens=2048,
            stream=False
        )
        soup = BeautifulSoup(response.choices[0].message.content, "html.parser")
        tweets = soup.find_all("tweet")
        return [tweet.text for tweet in tweets]


class Ref:
    custom_instructions = """
      please follow these instructions: {custom_instructions}
    """

    system_prompt = """
    You are assistant in generating viral tweets for the user. User comes up with one or more tweets and you will try to generate similar sounding (not exact) variants of them. Output 10 variations in following format:
    <tweets>
    <tweet>first tweet</tweet>
    ...
    <tweet>tenth tweet</tweet>
    </tweets>
    Do not output any other format or text, strictly above output.
    {custom_instructions}
    """

    tweet_prompt = """
    Here is the list of tweets:
    {tweets}
    Now generate 10 more variants that play on the same theme in the define format:
    """

if __name__ == "__main__":
    generator = TweetGenerator()
    tweets = ["Unit testing catches bugs early. Tweet Optimize catches weak tweets before they flop. Predict tweet success upfront."]
    print(generator.generate_tweets(tweets))
