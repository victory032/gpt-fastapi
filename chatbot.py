from fastapi import FastAPI, APIRouter, Request, File, UploadFile
from typing_extensions import Annotated

import re
import requests
from bs4 import BeautifulSoup
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
import pinecone
from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings

from langchain.document_loaders.csv_loader import CSVLoader
from langchain.document_loaders import PyPDFLoader
from langchain.document_loaders import UnstructuredWordDocumentLoader
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
from pydantic import BaseModel


router = APIRouter()
limit_count = 150

OPENAI_API_KEY = "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"
PINECONE_KEY = "81ce57b7-3808-4a19-abb3-48e74e0fb463"
PINECONE_ENV = "us-central1-gcp"

class Data(BaseModel):
    data: object
class UploadData(BaseModel):
    file: UploadFile
#------------------data-------------------------#
def saveTrainData(link):

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
    }

    response = requests.get(link, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
    all_text = ''

    for tag in tags:
        all_text += (tag.get_text() + '\n')
    try:
        with open('dtonomy.txt', 'w', encoding='utf-8') as f:
            f.write(all_text)
    except Exception as e:
        print(e)
    # return

#------------------crawling-------------------------#
def check_url(url, not_links):
    try:
        pattern = re.compile("\d{4}/\d{2}/\d{2}")
        if pattern.search(url):
            return False
        if init_url not in url:
            return False
        if url in not_links:
            return False
        if url[len(url)-1] != '/':
            return False
    except Exception as e:
        print(e)
        return False
    return True

def crawl_website():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
    }
    source_code = requests.get(init_url, headers=headers)
    soup = BeautifulSoup(source_code.content, 'lxml')
    links = []
    crawled_links = []

    for link in soup.find_all('a', href=True):
        sub_url = link.get('href')
        if check_url(sub_url, links):
            links.append(sub_url)
            print(sub_url)

    try:
        for link in links:
            if(len(links)>limit_count):
                break
            if link in crawled_links:
                continue
            sub_source_code = requests.get(link, headers=headers)
            sub_soup = BeautifulSoup(sub_source_code.content, 'lxml')
            crawled_links.append(link)

            for sub_link in sub_soup.find_all('a', href=True):
                sub_link_url = sub_link.get('href')
                if check_url(sub_link_url, links):
                    links.append(sub_link_url)
                    print(sub_link_url)
                    if(len(links)>limit_count):
                        break
    except Exception as e:
        print(e)

    return links


@router.get('/txtEmbed/')
def txt_embed(author, source_url):
    loader = UnstructuredFileLoader("dtonomy.txt")
    data = loader.load()
    data[0].metadata = {
        'author': author,
        'source': source_url,
    }
    # print(data[0].metadata)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=0)
    texts = text_splitter.split_documents(data)

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    # initialize pinecone
    pinecone.init(
        api_key=PINECONE_KEY,
        environment=PINECONE_ENV
    )
    index_name = "langchain-openai"
    namespace = "scraping"

    docsearch = Pinecone.from_texts(
      [t.page_content for t in texts], embeddings, [t.metadata for t in texts],
      index_name=index_name, namespace=namespace)
    
    #
    query = "please write 3 questions based on your embedded content"
    llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
    chain = load_qa_chain(llm, chain_type="stuff")

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    doclist = Pinecone.from_existing_index(index_name, embeddings, namespace=namespace)

    docs = doclist.similarity_search(query, include_metadata=True, namespace=namespace)

    answer = str(chain.run(input_documents=docs, question=query))
    #
    return{'success': 'success embedding', 'suggested questions': answer}

@router.post('/urlEmbed')
def url_embed(data: Data):
    temp = []
    for x in data.data:
        saveTrainData(x['url'])

        loader = UnstructuredFileLoader("dtonomy.txt")
        data = loader.load()
        data[0].metadata = {
            'author': x['author'],
            'source': x['source'],
        }
        temp.append(data)
    for data in temp:
        print(data, '\n')
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=0)
        texts = text_splitter.split_documents(data)

        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

        # initialize pinecone
        pinecone.init(
            api_key=PINECONE_KEY,
            environment=PINECONE_ENV
        )
        index_name = "langchain-openai"
        namespace = "scraping"

        docsearch = Pinecone.from_texts(
          [t.page_content for t in texts], embeddings, [t.metadata for t in texts],
          index_name=index_name, namespace=namespace)
    return{'success': 'success embedding'}

@router.post('/uploadfile')
async def upload_file(request: Request):
    # async with request.form() as form:
    #     filename = form["file"].filename
        # contents = await form["upload_file"].read()
    print(request.body)
    return {'success': 'success'}


@router.get('/getReply/{question}')
async def getReply(question):
    # links = crawl_website();
    # print('\n Finished Crawling \n')
    # savTrainData(init_url)
    # print('\n Finished Saving Files \n')e

    query = question
    print(question)

    llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
    chain = load_qa_chain(llm, chain_type="stuff")

    pinecone.init(
        api_key=PINECONE_KEY,
        environment=PINECONE_ENV
    )
    index_name = "langchain-openai"
    namespace = "scraping"

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    doclist = Pinecone.from_existing_index(index_name, embeddings, namespace=namespace)

    docs = doclist.similarity_search(query, include_metadata=True, namespace=namespace)

    answer = str(chain.run(input_documents=docs, question=query))

    return {"answer": answer, "related": docs}

@router.get("/")
def hello():
    return {"message":"Hello TutLinks.com"}

@router.get('/getSuggest/')
def get_suggest():

    pinecone.init(
        api_key=PINECONE_KEY,
        environment=PINECONE_ENV
    )

    index_name = "langchain-openai"
    namespace = "scraping"

    query = "please write 3 questions based on your embedded content"
    llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
    chain = load_qa_chain(llm, chain_type="stuff")

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    doclist = Pinecone.from_existing_index(index_name, embeddings, namespace=namespace)

    docs = doclist.similarity_search(query, include_metadata=True, namespace=namespace)

    answer = str(chain.run(input_documents=docs, question=query))

    return {'suggest': answer}