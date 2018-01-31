#!/usr/bin/python
"""
Copyright Cisco Systems, Inc.
2016 Qiang Tu 

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

# Import CherryPy global namespace
import sys
import cherrypy
from subprocess import call
#import subprocess32
import subprocess
import socket
import time
import pickle
from collections import OrderedDict
from cherrypy import wsgiserver
from cherrypy.lib.static import serve_file

class webAgent:
    runningAgent = {}
    psStr = 'ps | grep "agent run ../'
    dataDir = "/data/appdata/"
    """ Sample request handler class. """
    @cherrypy.expose
    def fileShow(self, filepath):
        if filepath.find('..') != -1 :
            return 'result:failure. Directory cannot contain ..'
        try:
            if not os.path.exists(self.dataDir + filepath):
                return 'result:failure. no such file'
            with open(self.dataDir + filepath, "r") as f:
                return f.read()
        except :    
            return "result:failure. unknown error"
        return "result:failure. unknown error"
    fileShow.exposed = True
    
    def fileDel(self , dir):
        if dir.find('..') != -1 :
            return {'result':'failure. Directory cannot contain ..'}
        try:
            if not os.path.exists(self.dataDir + dir):
                return {'result':'failure. no such directory'}
            cli = "rm -Rf " + self.dataDir + dir
            ret = os.popen(cli).read()
            print cli
            print ret
        except :    
            return {'result':'failure. no such directory'}
        return  {'result':'success'} 
    fileDel.exposed = True
    fileDel._cp_config = {'tools.json_out.on': True}

    def fileList(self , dir):
        if dir.find('..') != -1 :
            return {'result':'failure. Directory cannot contain ..'}
        filelist = []
        try:
            for f in os.listdir(self.dataDir + dir):
                if os.path.isfile(self.dataDir+dir +"/"+f):
                   print f
                   filelist.append(f)
        except :    
            return {'result':'failure. no such directory'}
        print filelist
        return  filelist   
    fileList.exposed = True
    fileList._cp_config = {'tools.json_out.on': True}


    def upload(self, dir, myFile):
        if dir.find('..') != -1 :
            return {'result':'failure. Directory cannot contain ..'}
        try:
            # Although this just counts the file length, it demonstrates
            # how to read large files in chunks instead of all at once.
            # CherryPy reads the uploaded file into a temporary file;
            # myFile.file.read reads from that.
            size = 0
            if not os.path.exists(self.dataDir + dir):
                os.makedirs(self.dataDir +dir)
            with open(self.dataDir +dir+"/"+myFile.filename, "wb") as f:
                while True:
                    data = myFile.file.read(8192)
                    if not data:
                        break
                    size += len(data)
                    if not data:
                        break
                    f.write(data)
        except:    
            return {'result':'failure.'}
        return {'result':'success.'}
    upload.exposed = True
    upload._cp_config = {'tools.json_out.on': True}

    def download(self, filepath):
        if filepath.find('..') != -1 :
            return {'result':'failure. Directory cannot contain ..'}
        return serve_file(self.dataDir + filepath, "application/x-download", "attachment")
    download.exposed = True
    
    def saveConfig(self):
        configFile = open('/home/root/webagent.cfg', 'wb')
        pickle.dump(self.runningAgent,configFile)
        configFile.close()
        return
    def __init__(self):
        try:
            ret = os.popen("cd /run ; agent /dev/null 2&>1").read()
            #time.sleep(3)
#            ret = os.popen("killall agent").read()
            configFile = open('/home/root/webagent.cfg', 'rb')
            self.runningAgent = pickle.load(configFile)
            configFile.close()
            for agentdir in self.runningAgent:
                if agentdir == "__south_ip" or agentdir == "__south_mask":
                    continue
                cli = "cd " + self.dataDir + agentdir + " ; ls *.cfg"
                ret = os.popen(cli).read()
                ary = ret.splitlines()
                if len(ary) > 0:
                    cli = "cd " + self.dataDir + agentdir + " ; agent run ../" + agentdir + "/" + ary[0] + " 1>/dev/null 2>/dev/null &"
                    print cli
                    ps = subprocess.call(cli,shell=True)
            if self.runningAgent.has_key('__south_ip') and  self.runningAgent.has_key('__south_mask'):
                cli = "ifconfig eth1 " + self.runningAgent['__south_ip'] + " netmask " + self.runningAgent['__south_mask'] + " 2>&1"
                print cli
                ps = os.popen(cli).read()
                    
        except:    
            print("empty configuration")
        
            
        return    
    def agentStart(self, agentdir ):
        if agentdir.find('..') != -1 :
            return {'result':'failure. Directory cannot contain ..'}
        if not os.path.exists(self.dataDir + agentdir):
            return {'result':'failure. Directory does not exist'}
        try:
            cli =  self.psStr + agentdir + '/"'
            ret = os.popen(cli).read()
            print ret
            ary = ret.splitlines()
            if len(ary) > 2:
                return {'result':'failure. alreay started'}
                
            cli = "cd " + self.dataDir + agentdir + " ; ls *.cfg"
            ret = os.popen(cli).read()
            print ret
            ary = ret.splitlines()
            if len(ary) == 0:
                return {'result':'failure. no configuration found'}
            
            
            cli = "cd " + self.dataDir + agentdir + " ; agent run ../" + agentdir + "/" + ary[0] + " 1>/dev/null 2>/dev/null &"
            print cli
            ps = subprocess.call(cli,shell=True)
            ct = 0
            time.sleep(2)
            while ct < 20:
                cli = self.psStr + agentdir + '/"'
                ret = os.popen(cli).read()
                print ret
                ary = ret.splitlines()
                if len(ary) > 2:
                    self.runningAgent[agentdir] = 1
                    self.saveConfig()
                    return {'result':'success'}
                ct += 10
                time.sleep(0.5)
                
            cli = "cd " + self.dataDir + agentdir + " ; ls *.log -t | head -n1"
            print cli
            ret = os.popen(cli).read()
            print ret
            cli = "cat " + self.dataDir + agentdir + "/"+ ret
            ret = os.popen(cli).read()
            print ret
            ary = ret.splitlines()
            ret = ''
            if len (ary) > 0:
                ret = ary[len(ary)-1]
            return {'result':'failure. ' + ret}
        except:    
            return {'result':'failure.'}
    agentStart.exposed = True
    agentStart._cp_config = {'tools.json_out.on': True}
    def agentStop(self, agentdir ):
        if agentdir.find('..') != -1 :
            return {'result':'failure. Directory cannot contain ..'}
        try:
            if self.runningAgent.has_key(agentdir):
                del self.runningAgent[agentdir]
                self.saveConfig()               
            cli = self.psStr + agentdir + '/"'
            ret = os.popen(cli).read()
            ary = ret.splitlines()
            pid = '0'
            for line in ary:
                if line.find('grep') == -1 and line != "":
                    ary = line.split()
                    pid = ary[0]
                    break
                    
            if pid == '0':
                return {'result':'failure. not started'}
            cli = 'kill ' + pid
            print cli
            ret = os.popen(cli).read()
            return {'result':'success'}
        except:    
            return {'result':'failure.'}
    agentStop.exposed = True
    agentStop._cp_config = {'tools.json_out.on': True}
    def agentList(self ):
        try:
            agentlist = {}
            for f in os.listdir(self.dataDir):
                if os.path.isdir(self.dataDir+f):
                    ps = os.popen("grep Devices " + self.dataDir +f + "/*.cfg").read()
                    if ps.find("Devices") != -1:
                        agentlist[f] = '0M'
            ps = os.popen("ps | grep 'agent run '").read()
            for line in ps.split("\n"):
                if line.find('grep') == -1 and line != "":
                   print line
                   ary = line.split()
                   start = ary[6].find("../")
                   end = ary[6].find("/", start+3)
                   str = ary[6]
                   print ary[6],start, end
                   str = str[start+3:end]
                   try:
                       num = int(ary[2])//1000 - 20
                   except :
                       num = 100                   
                   if num < 5:
                       num = 5
                   val = "%dM" % num
                   agentlist[str] = val
            ret = []
            for key, value in agentlist.iteritems():
                tmp = OrderedDict()
                tmp['dir'] = key
                if value == "0M":
                   tmp['status']= "stopped"
                else:
                   tmp['status']= "running"
                tmp['memory']=value
                ret.append(tmp)
            return ret
        except :    
            #print "Unexpected error:", sys.exc_info()[0]
            return {'result':'failure.'}
    agentList.exposed = True
    agentList._cp_config = {'tools.json_out.on': True}

    def setSouthIp(self, addr, mask ):
        cli = "ifconfig eth1 " + addr + " netmask " + mask + " 2>&1"
        print cli
        ps = os.popen(cli).read()
        print ps
        if len(ps) > 0:
            return {'result':'failure. ' + ps}
        self.runningAgent['__south_ip'] = addr
        self.runningAgent['__south_mask'] = mask
        self.saveConfig()               
        return {'result':'success'}
    setSouthIp.exposed = True
    setSouthIp._cp_config = {'tools.json_out.on': True}
        
    def getSouthIp(self):
        ps = os.popen("ifconfig eth1").read()
        ary = ps.split("\n")
        line = ary[1]
        if line.find('inet addr:') != -1:
            print line
            ary = line.split()
            addr = ary[1]
            tmp  = addr.split(':')
            addr = tmp[1]
            
            mask = ary[3]
            tmp  = mask.split(':')
            mask = tmp[1]
            tmp = OrderedDict()
            tmp['result'] = 'success'
            tmp['addr'] = addr
            tmp['mask'] = mask
            
            return tmp
        return {'result':'failure. no ip address found'}
    getSouthIp.exposed = True
    getSouthIp._cp_config = {'tools.json_out.on': True}

import os.path
tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

def validatePassword(realm, username, password):
    UDP_PORT = 6006

    ps = os.popen("ip route").read()
    ary = ps.split("\n")
    if len(ary) < 1:
        return False    
    line = ary[0]
    if line.find('default via') != -1:
        ary = line.split()
        UDP_IP = ary[2]
        print UDP_IP
    else:
        return False

    ps = os.popen("ifconfig eth0").read()
    ary = ps.split("\n")
    if len(ary) < 1:
        return False    
    line = ary[1]
    if line.find('inet addr:') != -1:
        ary = line.split()
        addr = ary[1]
        tmp  = addr.split(':')
        addr = tmp[1]
        print addr
    else:
        return False
    msg = " ".join((username , password))
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    sock.bind((addr, UDP_PORT))                        
    sock.sendto(msg, (UDP_IP, 6005))
    sock.setblocking(0)
    ct = 0
    while (ct < 10):
        try:
            data, addr = sock.recvfrom(1024)
        except socket.error:
            pass
        else:     
            print "received message:", data
            if data == 'success':
                return True
            else:
                return False
        time.sleep(1)
        print ct
        ct += 1
    
    return False

if __name__ == '__main__':
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to webAgent().index().
    enaAuth = {
       'tools.auth_basic.on': False,
       'tools.auth_basic.debug': False,
       'tools.auth_basic.realm': 'localhost',
       'tools.auth_basic.checkpassword': validatePassword,
        }
    conf = {
        '/': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': '/home/root/static',
        'tools.auth_basic.on': False,
        },
        '/fileDel': enaAuth,
        '/fileList': enaAuth,
        '/upload': enaAuth,
        '/download': enaAuth,
        '/agentStop': enaAuth,
        '/agentList': enaAuth,
        '/agentStart': enaAuth,
        '/setSouthIp': enaAuth,
        '/getSouthIp': enaAuth,
    }
    global_conf = {
        'server.socket_host': "0.0.0.0",
        'server.socket_port': 5010,
        'log.screen': False,
        'log.access_file': '',
        'log.error_file': '',
    }
    cherrypy.config.update(global_conf)
    sslModule = "builtin"
    adapterClass = wsgiserver.get_ssl_adapter_class(sslModule)
    sslAdapterInstance = adapterClass("ssl.crt", "ssl.key")
#    wsgiserver.CherryPyWSGIServer.ssl_adapter = sslAdapterInstance
    cherrypy.quickstart(webAgent(), config=conf)
    cherrypy.quickstart(webAgent())
else:
    # This branch is for the test suite; you can ignore it.
    cherrypy.tree.mount(webAgent(), config=tutconf)
