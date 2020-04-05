# -*- coding: utf-8 -*-
"""
@author: TheBetterKong
Created：2020/04/04
说明：
    1.切记：需要在电脑上安装ffmpeg
    2.在课程的视频下载中，如果有已上传的视频，当前不再访问时间，程序会出错，所以保证所有视频均可以下载的情况下使用；
    3.程序比较粗制滥造，可能存在一些bug，但是无伤大雅，主要是方便在疫情远程教学期间临时使用，所以先这样凑合着用了，如果期间出现问题，后续再进行改进；

感谢初稿程序的作者：Lu Song！！！
    地址：https://blog.csdn.net/lusongno1/article/details/79995009
    对比：
        1.旧版程序主要完成全部课程所有资源的批量下载，但我认为选课过多时，任务量太大，而且会有一些课程不需要下载其课件，所以我将其改成了按课程下载课件；
        2.在疫情远程上课期间，许多课程都采用了录播或直播的形式上课，有时候因为自己网速或者其他原因，会想将这些课程下载到本地观看，也便于日后复习。所以，
        我新增了课程视频的下载功能。

注意：下载下来的资源、视频，仅供自己学习观看，请不要传播！
"""

import requests
import re
import os
import subprocess
from bs4 import BeautifulSoup
import json
from urllib.parse import unquote



def save_html(html):
    f = open('test.html','w',encoding='utf-8')
    f.write(html)
    f.close



def UCAS_login():
    try:
        #读取登录信息
        config = open("user.txt", encoding='utf-8')
        line = config.readline().split()
        username = line[0]
        password = line[1]
    except IOError as e:
        print(e)
    session = requests.session()
    login_url = 'http://onestop.ucas.ac.cn/Ajax/Login/0'#提交信息地址，这个地址不需要验证码
    headers=  {
                'Host': 'onestop.ucas.ac.cn',
                "Connection": "keep-alive",
                'Referer': 'http://onestop.ucas.ac.cn/home/index',
                'X-Requested-With': 'XMLHttpRequest',
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36",
            }
    post_data = { # 构造表单数据
                "username": username,
                "password": password,
                "remember": 'checked',
            }
    html = session.post(login_url, data=post_data, headers=headers).text #请求，并建立session
    res = json.loads(html)  #注意区分：登录地址、提交数据地址、返回的地址这三点，这里打开返回的地址
    html = session.get(res['msg']).text
    print('登录系统成功！')
    #save_html(html)
    return session



def getinto_courseSite(session):
    url = "http://sep.ucas.ac.cn/portal/site/16/801"   #课程网站部分的地址
    # 利用正则表达式找Request URL，Identity后的身份认证信息
    h_k = session.get(url)
    key = re.findall(r'"https://course.ucas.ac.cn/portal/plogin\?Identity=(.*)"', h_k.text)[0]
    #利用得到的身份认证信息，打开课程网站系统
    url = "http://course.ucas.ac.cn/portal/plogin/main/index?Identity=" + key
    h = session.get(url)
    print('课程网站系统进入成功！')
    #save_html(h.text)
    page = h
    return page



def get_courseInfo(session,courseSite):
    course_list = []
    # 利用正则表达式，找到课程网站的主页地址，并进入主页
    mycourseBS = BeautifulSoup(courseSite.text,"lxml")
    mycourseBS.find_all('a',{"class":'Mrphs-toolsNav__menuitem--link'})
    url_mycourse = mycourseBS.find_all('a',{"class":'Mrphs-toolsNav__menuitem--link'})[0]
    url_mycourse = url_mycourse["href"]
    coursePage = session.get(url_mycourse)
    #save_html(coursePage.text)
    # 利用正则表达式，在课程网站主页，寻找课程信息，并利用元组的形式记录在course_list中
    coursePageBS = BeautifulSoup(coursePage.text,"lxml")
    Course_info = coursePageBS.find_all('li',{"class":"fav-sites-entry"})
    length = len(Course_info)
    print("*****************************************************************")
    print("所选课程总数为：",length)
    print(("已选课程列表："))
    for i in range(0,length-1):
        info = Course_info[i]
        tag = info.div.a
        courseName = tag["title"]  #课程名字
        print("   ",i,courseName)
        courseUrl = tag["href"]   #课程链接
        course_list.append((courseName,courseUrl)) #利用元组的形式保存
    print("*****************************************************************")
    return course_list



### 进入所选课程资源页面
def download_course_kj(courseID,courseInfo,session):
    summaryInfo = []
    course = courseInfo[courseID]
    currentClassName = course[0]
    url = course[1]
    # 利用正则表达式，找到对应课程界面里的资源模块，获取其url
    h = session.get(url)
    h_bs = BeautifulSoup(h.text, "lxml")
    url = h_bs.find_all(title="资源 - 上传、下载课件，发布文档，网址等信息")[0].get("href")
    print('进入%s课程资源页面中……' % currentClassName)
    downloadfile = getClass_kj(currentClassName, url, session, None)    # 当下载的课程资源里含有文件夹时，此函数返回值出错:downloadfile为空
    if downloadfile != []:
        summaryInfo.append((currentClassName, downloadfile))
    return summaryInfo


### 获取所选课程所有资源的链接
def getClass_kj(currentClass, url, session, data):
    if data != None:
        s = session.post(url, data=data)
        s = session.get(url)
    else:
        s = session.get(url)
    print('获取资源列表，寻找资源链接……')
    downloadfile = []
    # 找到该课程的所有资源节点（包括文件夹和文件）
    resourceList = BeautifulSoup(s.text, "html.parser").findAll("tr", {"class": ''})
    for ress in resourceList:
        flag = 0 #用来标记课件是否下载成功
        if ress.find("td") == None:
            continue
        if ress.find("input") == None:
            continue

        def parent_is_td(tag):
            return tag.parent.name == 'td' and tag.name == 'a'  #找父节点名为td，子节点名为a
        res = ress.find(parent_is_td)  # 返回资源节点（包括文件夹和文件）中符合这种要求的节点
        resUrl = res.get("href")  # 获取相关资源的下载链接

        if res.get("title") == "打开此文件夹":
            print('文件夹展开……')
            path = ress.find("td", {"headers": "checkboxes"}).input.get("value")
            sct = BeautifulSoup(s.text, "lxml").find(attrs={"name": "sakai_csrf_token"})
            sct = sct.get("value")
            data = {'source': '0', 'collectionId': path, 'navRoot': '', 'criteria': 'title',
                    'sakai_action': 'doNavigate',
                    'rt_action': '', 'selectedItemId': '', 'sakai_csrf_token': sct}
            urlNew = BeautifulSoup(s.text, "html.parser").find("form").get("action")
            print('文件夹展开链接为%s' % urlNew)
            getClass_kj(currentClass, urlNew, session, data)
        elif res.get("href") == "#":   # 有版权的文件，需要构造下载链接
            print('下载版权文件中……')
            jsStr = res.get("onclick")
            reg = re.compile(r"openCopyrightWindow\('(.*)','copyright")
            match = reg.match(jsStr)
            if match:
                resUrl = match.group(1)
                resName = resUrl.split("/")[-1]
                resName = unquote(resName)  # , encoding="GBK")
                flag = download_kj(resUrl, resName, currentClass, session)
        else:   # 课件可以直接下载的
            print('课件直接下载中……')
            resName = resUrl.split("/")[-1]
            resName = unquote(resName)  # , encoding="GBK")
            flag = download_kj(resUrl, resName, currentClass, session)
        if flag:
            downloadfile.append(resName)
    return downloadfile


### 按照获取到的课件资源链接进行下载
def download_kj(url, fileName, className, session):
    # \xa0转gbk会有错
    fileName = fileName.replace(u"\xa0", " ").replace(u"\xc2", "")
    # 去掉不合法的文件名字符
    fileName = re.sub(r"[/\\:*\"<>|?]", "", fileName)
    className = re.sub(r"[/\\:*\"<>|?]", "", className)

    dir = os.getcwd() + "/" + className
    file = os.getcwd() + "/" + className + "/" + fileName
    # 没有课程文件夹则创建
    if not os.path.exists(dir):
        os.mkdir(dir)
    # 存在该文件，返回
    if os.path.exists(file):
        print("%s已存在，就不下载了" % fileName)
        return 0
    print("开始下载%s..." % fileName)
    s = session.get(url)
    with open(file, "wb") as data:
        data.write(s.content)
    return 1



### 进入所选课程视频页面
def download_course_sp(courseID,courseInfo,session):
    summaryInfo = []
    course = courseInfo[courseID]  # 所选课程的course = (course_name , course_url)
    currentClassName = course[0]
    url = course[1]
    # 利用正则表达式，找到对应课程界面里的资源模块，获取其url
    h = session.get(url)
    h_bs = BeautifulSoup(h.text, "lxml")
    url = h_bs.find_all(title="课程视频 - 课程视频")[0].get("href")
    print('进入%s课程视频页面中……' % currentClassName)
    downloadfile = getClass_sp(currentClassName, url, session)
    #print(downloadfile)
    if downloadfile != []:
        summaryInfo = [currentClassName, downloadfile]
    #print(summaryInfo)
    return summaryInfo


### 进入课程视频页面后，获取所选课程所有视频的链接
def getClass_sp(currentClass, url, session):
    allpageURL = [] # 存视频所有页的链接
    sp_list = []  # 存放所有视频的信息，元组形式（spName，spUrl）
    # downloadfile = []
    VideoID = input("请选择下载的视频类型（0.课程视频 1.直播视频）：")
    print('获取资源列表，寻找资源链接……')

    if VideoID == "0": # 下载课程视频
        # 由于视频页可能包含多页，下面部分是抓取各个页的链接
        allpageURL.append(url)
        flag =1
        i = 0
        while flag:
            s = session.get(allpageURL[i])
            #save_html(s.text)
            page = re.search('<span><a href="([^上]*?)">下一页</a></span>',s.text, re.S)
            if page :
                page = page.groups()[0]
                pageURL = 'http://course.ucas.ac.cn' + page
                allpageURL.append(pageURL)
            else:
                flag = 0
            i = i+1
        # print(allpageURL)
        # 对每个页进行处理，获取所有视频的下载地址
        for pageurl in allpageURL :
            s = session.get(pageurl)
            List = BeautifulSoup(s.text, "lxml").find_all('div',attrs={"class": 'col_title'})
            for list in List:
                gotoplay = list.a['onclick']
                id = re.search("gotoPlay(.)'(.*?)','(\d+)'(.)", gotoplay, re.S).groups()[1]
                Url = 'https://course.ucas.ac.cn/portal/site/173754/tool/999d7ddb-4ec6-465f-8eaa-ac2ba8785d55/video/play?id='+id+'&type=u'
                htl = session.get(Url)
                spUrl = re.search('<source src="(.*?)" type="application/x-mpegURL">', htl.text, re.S).groups()[0]
                spName1 = list.a['title'].replace(':','-')
                spName = spName1.replace(' ','-')
                sp_list.append((spName, spUrl))
                print("正在下载：" + spName + "...\n视频较大，请耐心等待")
                download_sp(spName, spUrl)
        #print(sp_list)
    elif VideoID == "1": # 下载直播视频
        s = session.get(url)
        #save_html(s.text)
        zb_url ='https://course.ucas.ac.cn' + re.search('<span class=""><a href="(.*?)">直播视频</a></span>', s.text, re.S).groups()[0]
        s = session.get(zb_url) # 至此，已经进入到直播视频页面
        #save_html(s.text)
        siteId = re.search('var siteId = "(.*?)";', s.text, re.S).groups()[0]
        List = BeautifulSoup(s.text, "lxml").find_all('div', attrs={"class": 'col_img'})
        # 不同日期的直播视频文件夹，目前还没发现日期这里要分页的情况，就暂时不进行分页处理了
        for list in List:
            gotolist = list.a['onclick']
            recordingTime = re.search("gotoList(.)'(.*?)'(.);return(.*?);", gotolist, re.S).groups()[1]
            # 不同日期的直播视频地址
            dataurl = "https://course.ucas.ac.cn/portal/site/172716/tool/03adb157-3b44-4369-a88d-4cf859f5c644/video/recordList?siteId="+siteId+"&recordingTime="+recordingTime
            s = session.get(dataurl)
            #save_html(s.text)
            spList = BeautifulSoup(s.text, "lxml").find_all('div', attrs={"class": 'col_img'})
            for splist in spList:
                gotoPlay = splist.a['onclick']
                spName1 = splist.a['title'].replace(':','-')
                spName = spName1.replace(' ','-')
                id = re.search("gotoPlay(.)'(.*?)','(.*?)'(.);return(.*?);", gotoPlay, re.S).groups()[1]
                count = re.search("gotoPlay(.)'(.*?)','(.*?)'(.);return(.*?);", gotoPlay, re.S).groups()[2]
                # 视频播放地址
                Url = "https://course.ucas.ac.cn/portal/site/172716/tool/03adb157-3b44-4369-a88d-4cf859f5c644/video/play?id="+id+"&type=r&rank="+count
                # 寻找视频地址
                htl = session.get(Url)
                spUrl = re.search('<source src="(.*?)" type="application/x-mpegURL">', htl.text, re.S).groups()[0]
                sp_list.append((spName, spUrl))
                print("正在下载：" + spName + "...\n视频较大，请耐心等待")
                download_sp(spName, spUrl)
        #print(sp_list)
    return sp_list


### 按照获取到的视频链接调用ffmpeg进行下载
def download_sp(spName, spUrl):
    ins = 'ffmpeg -i ' + spUrl + ' -c copy ' + spName +'.mp4'
    p = subprocess.Popen(ins)
    p.wait()
    print('下载完毕')




if __name__ == '__main__':
    print(u"""#---------------------------------------  
#   程序：国科大课程网站OS程序   
#   作者：TheBetterKong 
#   日期：2020-04-04 
#   语言：Python 3.6  
#   操作：记事本第一行写入账号密码，空格隔开。  
#   功能：可以完成课程网站课件和视频的自动化下载
#---------------------------------------
""")
    print('系统登录中……')
    session = UCAS_login()
    print('进入课程网站中……')
    courseSite = getinto_courseSite(session)
    print('获取课程网站的课程中……')
    courseInfo = get_courseInfo(session, courseSite)

    gn = input("请选择功能（0.课件下载 1.课程视频下载）：")
    if gn == "0":
        courseID = int(input("请选择下载课程的课程编号："))
        course = courseInfo[courseID]
        print("# 所选课程为：",course[0])
        print("**********************************************")
        print('开始下载：')
        summary = download_course_kj(courseID, courseInfo, session)
        if summary != [] :
            print("**********************************************")
            print("# Report:\n%s课程有更新：" % course[0])
            info = summary[0]
            files = info[1]
            print("\n# 更新内容为：")
            for m in files:
                print("%s" % m)
            print("**********************************************")
        else:
            print("**********************************************")
            print("# Report:\n%s没有新课件下载！" % course[0])
            print("(#如果下载的课程资源里有文件夹存在，该Report不准确，请自行查看核对下载结果）")
            print("\n对于这个bug，十分抱歉！")
            print("这里没去修改是因为，这是由于程序逻辑出现的问题，修改起来比较麻烦；")
            print("而它只被作为临时使用，且该bug不影响主要功能，所以就没有仔细修改，如有需要，后续再进行改进。")
            print("**********************************************")
    elif gn == "1":
        courseID = int(input("请选择下载课程的课程编号："))
        course = courseInfo[courseID]
        print("# 所选课程为：", course[0])
        print("**********************************************")
        print('开始下载：')
        summary = download_course_sp(courseID, courseInfo, session)
        if summary != [] :
            print("**********************************************")
            print("# Report:\n%s课程有更新：" % course[0])
            print('\n更新内容为：')
            for sp in summary[1]:
                print(sp[0])
            print("**********************************************")
        else:
            print("**********************************************")
            print("# Report:\n%s没有新视频下载！" % course[0])
            print("**********************************************")



