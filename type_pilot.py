import asyncio
import aiohttp
import os
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, render_template

class WebResearchAssistant:
    def __init__(self):
        self.bing_api_key = os.getenv('BING_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')

    async def search_bing(self, query: str) -> List[Dict[str, str]]:
        """
        Perform a Bing search and return top 10 results.
        
        :param query: Search query
        :return: List of search results with URL and title
        """
        endpoint = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": self.bing_api_key
        }
        params = {
            "q": query,
            "count": 10
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            "url": result.get("url", ""),
                            "title": result.get("name", "")
                        } 
                        for result in data.get("webPages", {}).get("value", [])
                    ]
                else:
                    print(f"Bing Search Error: {response.status}")
                    return []

    async def fetch_webpage_content(self, url: str) -> str:
        """
        Fetch and extract text content from a webpage.
        
        :param url: URL of the webpage
        :return: Extracted text content
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove script, style, and navigation elements
                        for script in soup(["script", "style", "nav", "header", "footer"]):
                            script.decompose()
                        
                        # Extract text
                        text = soup.get_text(separator=' ', strip=True)
                        
                        # Cleanup excessive whitespace
                        text = ' '.join(text.split())

                        print("text is")
                        print(text[0:])

                        return text
                    else:
                        print(f"Failed to fetch {url}: {response.status}")
                        return ""
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    async def parallel_webpage_scraping(self, search_results: List[Dict[str, str]]) -> str:
        """
        Scrape webpages in parallel.
        
        :param search_results: List of search results
        :return: Consolidated text content
        """
        tasks = [self.fetch_webpage_content(result['url']) for result in search_results]
        contents = await asyncio.gather(*tasks)
        return ' '.join(filter(bool, contents))

    def summarize_with_gemini(self, text: str) -> str:
        """
        Use Gemini 1.5 Flash to summarize content.
        
        :param text: Input text to summarize
        :return: Summarized text
        """
        gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"""Summarize this text in exactly 300 words. 
                    Extract and highlight key numbers, statistics, and important details.
                    Ensure the summary is concise, clear, and captures the most significant information.
                    
                    Text to summarize:
                    {text}"""
                }]
            }]
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.gemini_api_key
        }
        
        response = requests.post(gemini_endpoint, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Gemini API Error: {response.status_code}")
            return ""

    async def research_and_summarize(self, query: str) -> str:
        """
        Perform complete research and also draw tables to show the numerical data if any make bullet points and summarize output.
        
        :param query: Research query
        :return: Final summary
        """
        # Search Bing for results
        search_results = await self.search_bing(query)

        #print("search results are")

        
        # Scrape webpages in parallel
        scraped_content = await self.parallel_webpage_scraping(search_results)

        # Summarize with Gemini
        summary = self.summarize_with_gemini(scraped_content)
        
        return summary

# Initialize Flask app
app = Flask(__name__)

# Add this route to handle the web form
@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ""
    if request.method == 'POST':
        query = request.form['query']
        # Initialize the WebResearchAssistant with your API keys
        assistant = WebResearchAssistant()
        # Run the research_and_summarize function asynchronously
        summary = asyncio.run(assistant.research_and_summarize(query))
    return render_template('index.html', summary=summary)

# Add this block to run the Flask app
if __name__ == "__main__":
    app.run(debug=True)