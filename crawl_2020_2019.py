from bs4 import BeautifulSoup
import urllib
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from tqdm.auto import tqdm
import pandas as pd
from pandas import DataFrame as df
import time
import re
import numpy as np

# 2019~2020 수집

urls = pd.read_csv('regions_202006261329#3.csv', encoding='CP949')
urls = urls.loc[89:]
urls.dropna(axis=0, subset=['url'], inplace=True)

all_tries = []
all_fails = []
failed_idx = []

# collect #
for idx, row in tqdm(urls.iterrows(), total=urls.shape[0]):
    district_name = row['belongs_to'] + ' ' + row['name']
    print('='*10, district_name, '시작', '='*10)

    options = webdriver.ChromeOptions()
    # options.add_argument('headless')
    options.add_argument('disable-gpu')
    options.add_argument('lang=ko_KR')
    # Chromedriver path
    driver = webdriver.Chrome(r'C:\Users\imsan\chromedriver.exe', chrome_options=options)

    eminwon = row['url']  # URL
    
    # get page, except close and move on #
    try:
        print(eminwon)
        driver.get(eminwon)
    except Exception:
        print('='*10, '접속 불가', '='*10)
        driver.close()
        failed_idx.append(idx)
        continue
    driver.implicitly_wait(5)
    
    try:
        # check if it's the right place, else close and move on #
        page_title = driver.title
        if re.search('목록조회', page_title):
            pass
        else:
            print('Wrong page, moving on')
            driver.close()
            failed_idx.append(idx)
            continue
    except Exception:
        print('='*10, '접속 불가', '='*10)
        # driver.close()
        failed_idx.append(idx)
        continue

    try:
        soup = BeautifulSoup(driver.page_source,'html.parser')
    except Exception:
        print('='*10, '접속 불량', '='*10)
        driver.close()
        failed_idx.append(idx)
        continue
    
    # if calendar is True, set date range
    if soup.find('input', {'id':'startDate'}):
        try:
            calender_toggle = '/html/body/main/div/form/div[1]/div[2]/div/img[1]'
            driver.find_element_by_xpath(calender_toggle).click()
            driver.implicitly_wait(1)

            for _ in range(5):
                driver.find_element_by_xpath('//*[@id="ui-datepicker-div"]/div/div/select[1]').send_keys(Keys.HOME)
            driver.find_element_by_xpath('//*[@id="ui-datepicker-div"]/div/div/select[2]').send_keys(Keys.HOME)

            calendar_soup = BeautifulSoup(driver.page_source,'html.parser')
            calendar = calendar_soup.find('table', {'class':'ui-datepicker-calendar'})

            target_date = calendar.find_all('tr')[1].find('td', {'data-handler':'selectDay'})
            target_date_number = calendar.find_all('tr')[1].find_all('td').index(target_date)

            driver.find_elements_by_xpath('//*[@id="ui-datepicker-div"]/table/tbody/tr[1]/td')[target_date_number].click()
            driver.find_element_by_xpath('//*[@id="searchBtn"]').click()
            
        except Exception:
            print('='*10+'달력 에러'+'='*10)
            driver.close()
            failed_idx.append(idx)
            continue
            
        driver.implicitly_wait(5)
        soup = BeautifulSoup(driver.page_source,'html.parser')
        soup = BeautifulSoup(driver.page_source,'html.parser')
        soup = BeautifulSoup(driver.page_source,'html.parser')
    else:
        pass
    
    # empty df for collecting data and later to_excel()
    result = df(columns = ['목록번호', '제목', '답변여부(처리기한)', '작성자', '작성일시', '결과통지여부', '민원내용', '담당부서', '답변일시', '답변내용'])
            
    # get post number of '이송이첩' and '다부처병렬'
    answer_status_list = [ans_status.get_text().strip() for ans_status in soup.find_all('td', {'class':'td-answer'})]
    submit_ans_nums = np.where(np.isin(np.array(answer_status_list), ['접수']))[0].tolist()
    processing_ans_nums = [postnum for postnum, post in enumerate(answer_status_list) if re.match('처리중', post)]
    trans_ans_nums = np.where(np.isin(np.array(answer_status_list), ['이송이첩']))[0].tolist()
    multi_ans_nums = np.where(np.isin(np.array(answer_status_list), ['다부처병렬']))[0].tolist()
    
    # count tries and errors
    try_ = 0
    fail_ = 0
    
    # set date range #
    # year = 2020
    _ = 0
    while True:
        
        # iter posts
        for i in range(20):

            if i in submit_ans_nums+processing_ans_nums:
                continue
            
            if re.search('목록조회', page_title):
                # idk
                try:
                    xpath = '//*[@id="dataSetTb"]/table/tbody/tr[{}]/td[4]'
                    year = int(driver.find_element_by_xpath(xpath.format(i+1)).text.strip()[:4])
                    if year < 2019:
                        break
                    else:
                        pass
                except: # assume page is on 상세목록 if error above
                    print('something wrong')
                    driver.back()
                    driver.implicitly_wait(1)
                    continue
            
            # click() a post #
            try:
                try_ += 1
                xpath = '//*[@id="dataSetTb"]/table/tbody/tr[{}]/td[2]/a'
                post_title_ = driver.find_element_by_xpath(xpath.format(i+1)).text
                if post_title_ == '[관리자에 의해 삭제되었습니다.]':
                    try_ -= 1
                    continue
                    
                list_title = post_title_.strip().split()
                # click() a post #
                driver.find_element_by_xpath(xpath.format(i+1)).click()
                driver.implicitly_wait(1)

                tables_should_be_2 = None
                t = 0
                while not tables_should_be_2 in [2, 3]:
                    minwon = driver.page_source
                    soup2 = BeautifulSoup(minwon,'html.parser')
                    tables_should_be_2 = len(soup2.find_all('table'))
                    t += 1
                    if t == 20:
                        break

                post_title = ''
                t = 0
                while post_title != list_title:
                    minwon = driver.page_source
                    soup2 = BeautifulSoup(minwon,'html.parser')
                    post_title = soup2.find_all('table')[0].find_all('td')[1].get_text().strip().split()
                    t += 1
                    if t == 20:
                        break
                
                # check page title
                if re.search('상세조회', driver.title):
                    pass
                else:
                    fail_ += 1
                    driver.back()
                    driver.implicitly_wait(1)
                    continue
                
            except Exception:
                fail_ += 1
                print('<Post Click Error> page:', _+1, 'post', i+1)
                
                if re.search('상세조회', page_title):
                    driver.back()
                    driver.implicitly_wait(1)
                    continue
                else:
                    continue
            
            try:  # get contents
                contents = []

                minwon_answer = soup2.find_all('table')
                for td in [0, 1, 2, 3, 6, -1]:  # select data from tds
                    contents.append(minwon_answer[0].find_all('td')[td].get_text().strip())

                # redirect popup cases #
                if i in trans_ans_nums+multi_ans_nums:
                    if i in trans_ans_nums:
                        handle = 1
                    elif i in multi_ans_nums:
                        handle = 2

                    xpath = '/html/body/main/div/table/tbody/tr/td/strong/a'
                    driver.find_element_by_xpath(xpath).click()
                    driver.implicitly_wait(1)
                    driver.switch_to.window(driver.window_handles[handle])

                    t = 0
                    pop_title = ''
                    while pop_title != '국민신문고':
                        soup_ech = BeautifulSoup(driver.page_source, 'html.parser')
                        pop_title = soup_ech.title.text
                        t += 1
                        if t == 20:
                            break

                    department = soup_ech.find_all('div', {'class':'mw_Input'})[handle].find('dd').get_text().strip()
                    ans_datetime = soup_ech.find('div', {'class':'answerBox'}).find_all('dd')[0].get_text().strip()
                    ans_text = soup_ech.find('div', {'class':'answerBox'}).find_all('dd')[1].get_text().strip()

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                    contents = contents + [department, ans_datetime, ans_text]    
                
                # normal cases #
                else:
                    for td in [0, 1, -1]:  # select data from tds
                        contents.append(minwon_answer[1].find_all('td')[td].get_text().strip())

                contents.insert(2, answer_status_list[i])
                result = result.append(pd.Series(contents, index=result.columns), ignore_index=True)


            except Exception:
                fail_ += 1
                title = soup2.find_all('table')[0].find_all('td')[1].get_text().strip()
                print('<Weird Post>', 'page:', _+1, 'post:', i+1, 'title:', title)
            
            t = 0
            while not re.search('목록조회', driver.title):
                t += 1
                driver.back()  # back() to post list page
                driver.implicitly_wait(2)
                if t == 20:
                    break
        
        if year < 2019:
            break
        
        try:
            driver.find_element_by_xpath('//*[@title="다음 페이지"]').click()  # go to next page
            driver.implicitly_wait(1)
            _ += 1
        except Exception:
            print('<Next Page Error>:', row['belongs_to'], row['name'])
            print('='*10+row['belongs_to']+' '+row['name']+' 실패!'+'='*10, end='\n\n')
            # driver.close()
            break

        soup3 = BeautifulSoup(driver.page_source,'html.parser')
        answer_status_list = [ans_status.get_text().strip() for ans_status in soup3.find_all('td', {'class':'td-answer'})]
        submit_ans_nums = np.where(np.isin(np.array(answer_status_list), ['접수']))[0].tolist()
        processing_ans_nums = [postnum for postnum, post in enumerate(answer_status_list) if re.match('처리중', post)]
        trans_ans_nums = np.where(np.isin(np.array(answer_status_list), ['이송이첩']))[0].tolist()
        multi_ans_nums = np.where(np.isin(np.array(answer_status_list), ['다부처병렬']))[0].tolist()
    
    # result
    all_tries.append(try_)
    all_fails.append(fail_)
    print('Tried {} posts and failed {} times'.format(try_, fail_))
    if try_ == 0:
        print('tried 0 post! why?')
    else:
        print('Success rate:', (try_-fail_)/try_)
    
    # save
    result.to_excel(row['belongs_to']+'_'+row['name']+'_새올민원.xlsx', index=False)
    print('='*10+row['belongs_to']+' '+row['name']+' 완료!'+'='*10, end='\n\n')

    driver.close()
