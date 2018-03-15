import socket, sys, os, datetime, time
from _thread import *

port = 12345
max_conn = 5
buffer_size = 8096
files = []

def start():
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(('', port))
		s.listen(max_conn)
		print ("Server Started Successfully")
	except Exception as e:
		print ("Unable to initialise socket because:",e)
		sys.exit(2)

	while(1):
		try:
			conn, addr = s.accept()
			data = conn.recv(buffer_size)
			(filename,t) = extractFilename(data)
			result = checkInCache(filename)
			if result:
				data = addIfModified(result, data)
			start_new_thread(conn_string, (conn, data, addr, result, filename))
		except KeyboardInterrupt:
			s.close()
			print ("Proxy Server Shutting Down")
			sys.exit(1)

	s.close()

def addIfModified(date, data):
	date = date[1]
	if(type(data) is bytes):
		temp = data.decode('ASCII')
	tempList = temp.split('\n')
	ifModifiedString = 'If-Modified-Since: ' + date + '\r'
	tempList.insert(-2,ifModifiedString)
	result = '\n'.join(tempList)
	return result

def extractFilename(data):
	if(type(data) is bytes):
		data = 	data.decode('ASCII')
	temp = data.split('\n')
	t = temp[0].split(' ')
	file = t[1].split('/')[3:]
	filename = '/'.join(file)
	return (filename,temp)

def modifyRequest(data):
	(filename,temp) = extractFilename(data)
	temp[0] = 'GET /' + filename +" HTTP/1.1\r"
	data = '\n'.join(temp)
	return data

def checkInCache(filename):
	for (i,(a,b,c)) in enumerate(files):
		if (a==filename):
			return (a,b,c,i)
	return False		

def conn_string(conn, data, addr, result, filename):
	try:
		if(type(data) is bytes):
			data = data.decode('ASCII')
		first = data.split('\n')[0].strip()
		url = first.split(' ')[1].strip()
		http_pos = url.find("://")
		if http_pos == -1:
			temp = url
		else:
			temp = url[(http_pos + 3):]
		port_pos = temp.find(":")
		web_pos = temp.find("/")
		if web_pos == -1:
			web_pos = len(temp)
		web = ""
		port1 = -1
		if port_pos == -1 or web_pos < port_pos:
			port1 = 20000
			web = temp[:web_pos]
		else:
			port1 = int((temp[(port_pos + 1):])[:web_pos - port_pos - 1])	
			web = temp[:port_pos]
		proxy_server(web, port1, conn, addr, data, result, filename)
	except Exception as e:
		pass

def checkStatusCode(response):
	if (type(response) is bytes):
		response = response.decode('ASCII')
	resp = response.split("\n")[0]
	statusCode = resp.split(" ")[1]
	return statusCode

def proxy_server(web, port1, conn, addr, data, result, filename):
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((web, port1))
		data = modifyRequest(data)
		if(type(data) is str):
			data = data.encode('ASCII')
		s.send(data)
		flag = -1
		flg = -1
		while 1:
			reply = s.recv(buffer_size)
			if (flag==-1 and flg==-1):
				stat = checkStatusCode(reply)
			if(result and stat=='304'):
				reply = result[2]
			elif(result and stat=='200'):
				temp = files[result[3]]
				now = datetime.datetime.now()
				date = now.strftime("%a %b  %d %H:%M:%S GMT %Y")
				if (flg==-1):
					files[result[3]] = (temp[0],date,reply)
					flg = result[3]
				else:
					files[flg] = (temp[0],date,files[flg][2]+reply)
			elif (not result):
				now = datetime.datetime.now()
				date = now.strftime("%a %b  %d %H:%M:%S GMT %Y")

				entry = (filename,date,reply)
				if(flag==-1):
					if(len(files)>=3):
						oldestElem = min(files,key=lambda t:time.strptime(t[1],'%a %b  %d %H:%M:%S GMT %Y'))
						files.pop(files.index(oldestElem))
					files.append(entry)
					flag = files.index(entry)
				else:
					files[flag] = (files[flag][0],files[flag][1],files[flag][2]+reply)
			if len(reply) > 0:
				conn.send(reply)
				dar = float(len(reply))
				dar = float(dar / 1024)
				dar = "%.3s" % (str(dar))
				dar = "%s KB" % (dar)
				print ("Request done: %s => %s <=" % (str(addr[0]), str(dar)))
			else:
				break
		s.close()
		conn.close()
	except socket.error as e:
		s.close()
		conn.close()
		sys.exit(1)

start()
