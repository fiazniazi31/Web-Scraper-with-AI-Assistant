# 🕷️ Web Scraper with AI Assistant (Streamlit + SQL + LangChain + Groq)

This project is a **web scraping and AI-powered data querying app** built with **Python, Streamlit**, and **SQL Server**. It allows users to scrape content from a website, store it in a **MSSQL database**, and interact with the scraped data using **natural language queries** powered by **LangChain** and **Groq's LLaMA 3**.

---

## 📦 Features

- 🌐 Scrape multiple pages from a target domain
- 🧠 Ask AI questions about the scraped data using Groq + LangChain
- 🗃️ Save data to Microsoft SQL Server
- 📊 View, export, or clear scraped data
- 🛠️ Built-in error handling and user-friendly interface via Streamlit

---

## 🚀 Technologies Used

- **Python 3**
- **Streamlit** (UI)
- **BeautifulSoup** (Web Scraping)
- **Requests** (HTTP Requests)
- **PyODBC** (SQL Server connectivity)
- **LangChain** (SQL Agent)
- **Groq** (LLM Provider)
- **Pandas** (Data Handling)
- **MSSQL Server** (Data Storage)

---

📂 File Structure
text
Copy
Edit
├── main.py               # Main Streamlit app
├── requirements.txt     # Python dependencies
├── .gitignore           # Files to ignore in Git (e.g., .env, venv/)
├── README.md            # This file


##For Install Dependencies

pip install -r requirements.txt


🧠 Sample Questions You Can Ask the AI
What are the main topics in the scraped content?

How many pages were scraped from a specific website?

Show me titles that include the word "Python"

What are the most recent URLs scraped?


👨‍💻 Author
Created by [Fiaz Khan]


📬 Feedback
If you encounter issues or have suggestions, feel free to open an issue or submit a pull request!
