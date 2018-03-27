#!/home/emilien/.pyenv/shims/python
# -*- coding: utf-8 -*-
import requests
import re
from bs4 import BeautifulSoup
import csv

from pymongo import MongoClient
client = MongoClient()
client = MongoClient("mongodb://localhost:27017")
db = client.babyhome
posts = db.babyhome
#mongodb connection setting

import rethinkdb as r
conn = r.connect()
try:
    r.db_create('babyhome').run(conn)
except:
    pass
conn.use('babyhome')
try:
    r.table_create('babyhome', primary_key="id").run(conn)
except:
    pass
#rethinkdb connection setting

unfilte_linklist = []
url_list = []
filte_list=[]

def get_unclean_link(url):
    soup = BeautifulSoup(requests.get(url).text, 'lxml')
    #soup is bs4.BeautifulSoup
    soup1 = soup.select("div > p.media-heading")
    #soup1 is a bs4 tag list
    for i in soup1:
        unfilte_linklist.append(i)
        #i is bs4.element.Tag


def filte_article(unfilte_linklist):
    for link in unfilte_linklist:
        filte_list.append(link.find('a', {'title': re.compile('.*')}))



def get_url(filte_list):
    for url in filte_list:
        if url in url_list:
            break
        else:
            url_list.append(url['href'])


def get_soup(url):
    try:
        data = {}
        question1_list = []
        reply_list = []
        soup = BeautifulSoup(requests.get(url).text, 'lxml')
        soup1 = soup.select_one("div > h1")
        author = soup.select_one('span.ellipsis')
        # here only on condition match so we use select_one, if there are more tag match we should use select

        data['author'] = author.text

        times = soup.select_one("p.floors.pull-right").text
        data['times'] = times.replace("版主", '').strip()
        data['title'] = soup1.text
        question0 = soup.select_one("li.media.thread-individual")
        question1 = question0.select('div.thread-inner')
        for y in question1:
            try:
                y.select('button.btn')[0].extract()
                # remove button.btn
                y.select('button.btn')[0].extract()
            except:
                pass
            try:
                # remove div class="" type
                y.select('div.')[0].extract()
            except:
                pass
            try:
                # remove quote.clearfix need to ask why can use quote.clearfix
                y.select('div.quote.clearfix')[0].extract()
            except:
                pass
            try:
                # remove div.edited-comment
                y.select('div.edited-comment')[0].extract()
            except:
                pass
            try:
                # remove div.edited-comment
                y.select('span.time-tag')[0].extract()
            except:
                pass
            try:
                if y.text.strip() == '【此則發言因違反討論區規則或其他原因，已被刪除】':
                    break
                else:
                    question1_list.append(y.text.strip())
            except:
                pass
        data['ask'] = ''.join(question1_list)
        comment = soup.select("li.media.thread-individual")
        del comment[0]
        # get frist page comment
        reply_list.append(get_comment(comment))
        next_page = soup.select_one('ul.pagination.pull-right')  # need to ask why can use like that
        # get after frist page comment
        next_url_check = next_page.find_all('li', {'class': re.compile('active')})
        next_url = next_page.select('li > a')
        try:
            if '1' in next_url_check[0].text:
                del next_url[-1]
                del next_url[0]
                del next_url[0]
                for url in next_url:
                    a = 'https://forum.babyhome.com.tw' + url['href']
                    comment_soup = BeautifulSoup(requests.get(a).text, 'lxml')
                    comment1 = comment_soup.select("li.media.thread-individual")
                    reply_list.append(get_comment(comment1))
            else:
                pass
        except:
            pass
        data['reply'] = sum(reply_list, [])
        # flat list
        data['url'] = soup.find('meta', {'content': re.compile('https://forum.babyhome.com.tw/topic/.*')})['content']
        data['_id'] = soup.find('meta', {'content': re.compile('https://forum.babyhome.com.tw/topic/.*')})['content'][36:]
        data['id'] = soup.find('meta', {'content': re.compile('https://forum.babyhome.com.tw/topic/.*')})['content'][36:]

        if r.db('babyhome').table('babyhome').get(data['id']).run(conn) == None:
            r.db('babyhome').table('babyhome').insert(data).run(conn)
        else:
            r.db('babyhome').table('babyhome').get(data['id']).update({"ask": data['ask'], 'reply': data['reply']}).run(conn)

        # insert to rethinkdb
        try:
            posts.insert_one(data)
        except:
            posts.delete_one({"_id": data['_id']})
            posts.insert_one(data)
    except:
        pass
    # insert to mongodb

def get_comment(comment):
    reply_list=[]
    for x in comment:
        comment_list=[]
        reply={}
        try:
            reply['author']=x.select_one('span.ellipsis').text
        except:
            pass
        z = x.select('div.thread-inner')
        for y in z:
            try:
                y.select('button.btn')[0].extract()
                #remove button.btn
                y.select('button.btn')[0].extract()
            except:
                pass
            try:
                #remove div class="" type
                y.select('div.')[0].extract()
            except:
                pass
            try:
                #remove quote.clearfix need to ask why can use quote.clearfix
                y.select('div.quote.clearfix')[0].extract()
            except:
                pass
            try:
                #remove div.edited-comment
                y.select('div.edited-comment')[0].extract()
            except:
                pass
            try:
                if y.text.strip() == '【此則發言因違反討論區規則或其他原因，已被刪除】':
                    break
                else:
                    comment_list.append(y.text.strip())
            except:
                pass
            reply['comment'] = ''.join(comment_list)
            #remove list making a new string
            reply_list.append(reply)
    return reply_list

url = 'https://forum.babyhome.com.tw/list/1047?year=all&page={}'

for num in range(301,400):
     get_unclean_link(url.format(num))

filte_article(unfilte_linklist)

get_url(filte_list)

for url in url_list:
    get_soup(url)

client.close()
conn.close()