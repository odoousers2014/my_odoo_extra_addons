#! /usr/bin/env python
#coding=utf-8
import web

urls = (
    '/*.*', 'index'
)

class index:
    def GET(self):
        return u"Service is updateting, \n服务器升级中，请稍后访问，谢谢"

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()

