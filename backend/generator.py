import dotenv
dotenv.load_dotenv()
import os
from openai import OpenAI
from bs4 import BeautifulSoup


class TweetGenerator:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def generate_tweets(self, tweets: list[str]) -> list[str]:
        tweets_str = "\n".join([f"<tweet>{tweet}</tweet>" for tweet in tweets])
        tweet_prompt = Ref.tweet_prompt.format(tweets=tweets_str)
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": Ref.system_prompt},
                {"role": "user", "content": tweet_prompt}
            ],
            max_completion_tokens=2048,
        )
        soup = BeautifulSoup(response.choices[0].message.content, "html.parser")
        tweets = soup.find_all("tweet")
        return [tweet.text for tweet in tweets]


class Ref:
    system_prompt = """
    You are assistant in generating viral tweets for the user. User comes up with one or more tweets and you will try to generate similar sounding (not exact) variants of them. Output 10 variations in following format:
    <tweets>
    <tweet>first tweet</tweet>
    ...
    <tweet>tenth tweet</tweet>
    </tweets>
    Do not output any other format or text, strictly above output.
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
