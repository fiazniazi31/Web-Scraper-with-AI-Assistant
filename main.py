import streamlit as st
import requests
from bs4 import BeautifulSoup
import pyodbc
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import re
from datetime import datetime

# LangChain imports for SQL Agent
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_groq import ChatGroq

# Database connection string
from dotenv import load_dotenv
load_dotenv()

import os
conn_str = os.getenv("SQL_CONN_STR")


def create_database_table():
    """Create the scraped_data table if it doesn't exist"""
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        create_table_query = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='scraped_data' AND xtype='U')
        CREATE TABLE scraped_data (
            id INT IDENTITY(1,1) PRIMARY KEY,
            url NVARCHAR(MAX),
            title NVARCHAR(MAX),
            content NVARCHAR(MAX),
            scraped_at DATETIME DEFAULT GETDATE()
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database table creation error: {str(e)}")
        return False

def get_page_links(base_url, max_pages):
    """Extract links from the base URL to scrape multiple pages"""
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        links.append(base_url)  # Include the base URL itself
        
        # Find all links on the page
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Check if it's a valid URL from the same domain
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                if full_url not in links:
                    links.append(full_url)
                    
                if len(links) >= max_pages:
                    break
        
        return links[:max_pages]
    except Exception as e:
        st.error(f"Error getting page links: {str(e)}")
        return [base_url]

def scrape_page(url):
    """Scrape content from a single page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No Title"
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text content
        content = soup.get_text()
        
        # Clean up the text
        lines = (line.strip() for line in content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        content_text = ' '.join(chunk for chunk in chunks if chunk)
        
        return {
            'url': url,
            'title': title_text,
            'content': content_text[:5000]  # Limit content length
        }
    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        return None

def save_to_database(data):
    """Save scraped data to MSSQL database"""
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO scraped_data (url, title, content)
        VALUES (?, ?, ?)
        """
        
        cursor.execute(insert_query, (data['url'], data['title'], data['content']))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database save error: {str(e)}")
        return False

def get_scraped_data():
    """Retrieve scraped data from database"""
    try:
        conn = pyodbc.connect(conn_str)
        query = "SELECT * FROM scraped_data ORDER BY scraped_at DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database retrieval error: {str(e)}")
        return pd.DataFrame()

def clear_database(u):
    """Clear all data from the database or specific url"""
    # print(f"deleting data from {u}")
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM scraped_data WHERE url LIKE \'{u}%\'')
        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        st.error(f"Database clear error: {str(e)}")
        return False

def agent_sql_tool(user_text, api_key):
    """SQL Agent tool to query scraped data"""
    try:
        # Initialize LLM with user-provided API key
        llm = ChatGroq(api_key=api_key, model_name="llama3-8b-8192")

        # Setup LangChain database and agent with the same connection string
        db = SQLDatabase.from_uri(f"mssql+pyodbc:///?odbc_connect={conn_str}")
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        agent_executor = create_sql_agent(llm=llm, toolkit=toolkit, verbose=True)
        
        return agent_executor.run(user_text)
    except Exception as e:
        st.error(f"Agent error: {str(e)}")
        return None

# Streamlit App
def main():
    st.set_page_config(page_title="Web Scraper with AI Assistant", layout="wide")
    
    st.title("🕷️ Web Scraper with AI Assistant")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("🔐 API Configuration")
    
    # Groq API Key input
    user_api_key = st.sidebar.text_input("Enter your Groq API Key:", type="password")
    url1 = "https://console.groq.com/home"
    url2 = "https://console.groq.com/keys"
    st.sidebar.write("If you don't have key create Groq Account [here](%s)" % url1)
    st.sidebar.markdown("Then after (Sign In) to create your API key [Click Here](%s)" % url2)
    
    st.sidebar.markdown("---")
    st.sidebar.header("Scraping Configuration")
    
    # URL input
    url = st.sidebar.text_input(
        "Website URL",
        placeholder="https://example.com",
        help="Enter the URL of the website you want to scrape"
    )
    
    # Number of pages
    num_pages = st.sidebar.number_input(
        "Number of Pages",
        min_value=1,
        max_value=50,
        value=5,
        help="Maximum number of pages to scrape from the website"
    )
    
    # Scrape button
    scrape_button = st.sidebar.button("🚀 Start Scraping", type="primary")
    
    st.sidebar.markdown("---")
    
    # Database controls
    st.sidebar.header("Database Controls")
    view_data_button = st.sidebar.button("📊 View Scraped Data")
    clear_data_button = st.sidebar.button("🗑️ Clear Database", type="secondary")
    
    # Initialize database table
    if 'db_initialized' not in st.session_state:
        st.session_state.db_initialized = create_database_table()
    
    # Create tabs for different functionalities
    tab1, tab2 = st.tabs(["🕷️ Web Scraping", "🤖 AI Assistant"])
    
    with tab1:
        # Web Scraping Tab Content
        if scrape_button and url:
            if not url.startswith(('http://', 'https://')):
                st.error("Please enter a valid URL starting with http:// or https://")
                return
            
            st.info(f"Starting to scrape {num_pages} pages from: {url}")
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Get page links
            status_text.text("Getting page links...")
            links = get_page_links(url, num_pages)
            
            if not links:
                st.error("Could not find any pages to scrape.")
                return
            
            st.success(f"Found {len(links)} pages to scrape")
            
            # Scrape each page
            scraped_count = 0
            for i, link in enumerate(links):
                status_text.text(f"Scraping page {i+1}/{len(links)}: {link}")
                
                # Scrape the page
                data = scrape_page(link)
                
                if data:
                    # Save to database
                    if save_to_database(data):
                        scraped_count += 1
                        st.success(f"✅ Scraped and saved: {data['title']}")
                    else:
                        st.error(f"❌ Failed to save: {link}")
                
                # Update progress
                progress_bar.progress((i + 1) / len(links))
                
                # Add delay to be respectful to the server
                time.sleep(1)
            
            status_text.text("Scraping completed!")
            st.success(f"🎉 Successfully scraped {scraped_count} out of {len(links)} pages!")
            
            # Show summary
            st.markdown("### Scraping Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pages", len(links))
            with col2:
                st.metric("Successfully Scraped", scraped_count)
            with col3:
                st.metric("Success Rate", f"{(scraped_count/len(links)*100):.1f}%")
        
        # View scraped data
        if view_data_button:
            st.markdown("### 📊 Scraped Data from Database")
            df = get_scraped_data()
            
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                
                # Download option
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No data found in the database. Start scraping to see data here.")
        
        # Clear database
        if clear_data_button:
                        
            if clear_database(url):
                # print(f"{url}data deleated...")
                st.success("Database cleared successfully!")
            else:
                st.error("Failed to clear database.")
        
        # Instructions for scraping
        if not scrape_button:
            st.markdown("""
            ### 📋 How to Use Web Scraping:
            1. **Enter URL**: Paste the website URL you want to scrape in the sidebar
            2. **Set Pages**: Choose how many pages to scrape (maximum 50)
            3. **Start Scraping**: Click the "Start Scraping" button
            4. **View Data**: Use "View Scraped Data" to see results from the database
            5. **Download**: Export your data as CSV file
            6. **Clear Data**: Remove all data from the database if needed
            
            ### 🔧 Features:
            - Scrapes multiple pages from the same domain
            - Stores data in MSSQL Server database
            - Progress tracking with visual feedback
            - Export data to CSV format
            - Respectful scraping with delays
            - Error handling and validation
            """)
    
    with tab2:
        # AI Assistant Tab Content
        if user_api_key:
            st.markdown("### 🤖 Ask Questions About Your Scraped Data")
            st.info("You can ask questions about the scraped data stored in your database. The AI will analyze the content and provide answers.")
            
            # Initialize chat history
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Display chat history
            for i, (question, answer) in enumerate(st.session_state.chat_history):
                with st.container():
                    st.markdown(f"**🙋‍♂️ You:** {question}")
                    st.markdown(f"**🤖 AI:** {answer}")
                    st.markdown("---")
            
            # User input for questions
            user_question = st.text_input("Ask a question about your scraped data:", 
                                        placeholder="e.g., What are the main topics in the scraped content?")
            
            col1, col2 = st.columns([1, 4])
            with col1:
                ask_button = st.button("🚀 Ask AI", type="primary")
            with col2:
                if st.button("🗑️ Clear Chat"):
                    st.session_state.chat_history = []
                    st.rerun()
            
            if ask_button and user_question:
                with st.spinner("🧠 AI is thinking..."):
                    try:
                        response = agent_sql_tool(user_question, user_api_key)
                        if response:
                            # Add to chat history
                            st.session_state.chat_history.append((user_question, response))
                            st.rerun()
                        else:
                            st.error("❌ Failed to get response from AI agent.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            # # Sample questions
            # st.markdown("### 💡 Sample Questions You Can Ask:")
            # sample_questions = [
            #     "How many pages were scraped from each website?",
            #     "What are the most common words in the scraped content?",
            #     "Show me all titles that contain specific keywords",
            #     "What websites have been scraped recently?",
            #     "Give me a summary of the content from a specific URL",
            #     "How many pages were scraped today?",
            #     "What are the longest articles in the database?"
            # ]
            
            # for question in sample_questions:
            #     if st.button(f"📝 {question}", key=f"sample_{question}"):
            #         with st.spinner("🧠 AI is thinking..."):
            #             try:
            #                 response = agent_sql_tool(question, user_api_key)
            #                 if response:
            #                     st.session_state.chat_history.append((question, response))
            #                     st.rerun()
            #             except Exception as e:
            #                 st.error(f"❌ Error: {str(e)}")
        
        else:
            st.markdown("### 🤖 AI Assistant - Query Your Scraped Data")
            st.warning("⚠️ Please enter your Groq API key in the sidebar to use the AI Assistant.")
            st.markdown("""
            ### 🧠 AI Assistant Features:
            - **Natural Language Queries**: Ask questions in plain English
            - **Data Analysis**: Get insights from your scraped content
            - **SQL Generation**: AI automatically generates SQL queries
            - **Smart Responses**: Contextual answers based on your data
            """)

if __name__ == "__main__":
    main()