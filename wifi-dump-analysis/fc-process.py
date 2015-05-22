#Author : Abhinav Narain
#Date : Jan 30, 2012
#Purpose : To read the binary files with data from BISmark deployment in homes

import os,sys,re
import gzip
import struct 


from  header import *
from mac_parser import * 
from stats import *

try:
    import cPickle as pickle
except ImportError:
    import pickle

missing_files=[]
noise_map=defaultdict(list)

if len(sys.argv) !=5:	
	print len(sys.argv)
	print "Usage : python reader.py data/<data.gz> mgmt/<mgmt.gz> ctrl/<ctrl.gz> <fc_count_filename>"
	sys.exit(1)
#compare regular expression for filenameif argv[1]

data_f_dir=sys.argv[1]
mgmt_f_dir=sys.argv[2]
ctrl_f_dir=sys.argv[3]
output_fc_filename=sys.argv[4]

data_fs=os.listdir(data_f_dir)
ctrl_fs=os.listdir(ctrl_f_dir)

data_file_header_byte_count=0
ctrl_file_header_byte_count=0
mgmt_file_header_byte_count=0
file_counter=0
file_timestamp=0
for data_f_name in data_fs :
    data_f= gzip.open(data_f_dir+data_f_name,'rb')
    data_file_content=data_f.read()
    data_f.close()
    data_file_current_timestamp=0
    data_file_seq_n=0
    bismark_id_data_file=0
    start_64_timestamp_data_file=0
    for i in xrange(len(data_file_content )):
        if data_file_content[i]=='\n':
            bismark_data_file_header = str(data_file_content[0:i])
            ents= bismark_data_file_header.split(' ')
            bismark_id_data_file=ents[0]
            start_64_timestamp_data_file= int(ents[1])
            data_file_seq_no= int(ents[2])
            data_file_current_timestamp=int(ents[3])
            data_file_header_byte_count =i
            break

    data_contents=data_file_content.split('\n----\n')
    header_and_correct_data_frames = data_contents[0]
    err_data_frames = data_contents[1]
    correct_data_frames_missed=data_contents[2]
    err_data_frames_missed=data_contents[3]

    ctrl_f_name = data_f_name
    ctrl_f_name =re.sub("-d-","-c-",ctrl_f_name)

    try :
        ctrl_f= gzip.open(ctrl_f_dir+ctrl_f_name,'rb')	
        ctrl_file_content=ctrl_f.read()
    except :
        print  "CTRL file not present ", ctrl_f_name 
        missing_files.append([ctrl_f_name,data_file_current_timestamp])
        continue 
    ctrl_f.close()
    
    
    mgmt_f_name = data_f_name
    mgmt_f_name = re.sub("-d-","-m-",mgmt_f_name)
    try : 
        mgmt_f= gzip.open(mgmt_f_dir+mgmt_f_name,'rb')
        mgmt_file_content=mgmt_f.read()
    except :
        print "MGMT file not present ",mgmt_f_name 
        missing_files.append([mgmt_f_name,data_file_current_timestamp])
        continue 

    mgmt_f.close()

    mgmt_file_current_timestamp=0
    mgmt_file_seq_no=0
    bismark_id_mgmt_file=0
    start_64_timestamp_mgmt_file=0
	
    ctrl_file_current_timestamp=0
    ctrl_file_seq_no=0
    bismark_id_ctrl_file=0
    start_64_timestamp_ctrl_file=0
    #frame_coint[timestamp].append([mgmt missed+collected correct,missed+collected incorr])

    for i in xrange(len(mgmt_file_content )):
        if mgmt_file_content[i]=='\n':
            bismark_mgmt_file_header = str(mgmt_file_content[0:i])
            ents= bismark_mgmt_file_header.split(' ')
            bismark_id_mgmt_file=ents[0]
            start_64_timestamp_mgmt_file=int(ents[1])
            mgmt_file_seq_no= int(ents[2])
            mgmt_file_current_timestamp= int(ents[3])
            mgmt_file_header_byte_count =i
            break
    mgmt_contents=mgmt_file_content.split('\n----\n')
    header_and_beacon_mgmt_frames = mgmt_contents[0] 
    common_mgmt_frames = mgmt_contents[1]
    err_mgmt_frames=mgmt_contents[2]
    beacon_mgmt_frames_missed=mgmt_contents[3]
    common_mgmt_frames_missed=mgmt_contents[4]
    err_mgmt_frames_missed=mgmt_contents[5]

    for i in xrange(len(ctrl_file_content )):
        if ctrl_file_content[i]=='\n':
            bismark_ctrl_file_header = str(ctrl_file_content[0:i])
            ents= bismark_ctrl_file_header.split(' ')
            bismark_id_ctrl_file= ents[0]
            start_64_timestamp_ctrl_file= int(ents[1])
            ctrl_file_seq_no= int(ents[2])
            ctrl_file_current_timestamp=int(ents[3])
            ctrl_file_header_byte_count =i
            break
    ctrl_contents=ctrl_file_content.split('\n----\n')
    header_and_correct_ctrl_frames = ctrl_contents[0]
    err_ctrl_frames = ctrl_contents[1]
    correct_ctrl_frames_missed=ctrl_contents[2]
    err_ctrl_frames_missed=ctrl_contents[3]
    #done with reading the binary blobs from file ; now check for timestamps are correct
    if (not (ctrl_file_current_timestamp == mgmt_file_current_timestamp == data_file_current_timestamp )) :
        print "timestamps don't match " 		
        sys.exit(1)
    else :
        file_timestamp=ctrl_file_current_timestamp	
    if (not (ctrl_file_seq_no == mgmt_file_seq_no == data_file_seq_no)):
        print "sequence number don't match "
        sys.exit(1)

	
    if (len(ctrl_contents) != 4 or  len(data_contents) != 4 or len(mgmt_contents) !=6) :
        print "for ctrl " ,len (ctrl_contents) ,"for data", len(data_contents), "for mgmt", len(mgmt_contents) 
        print "file is malformed or the order of input folders is wrong "
        continue 
	
        #The following code block parses the data file 	
    val_data_missed= list(struct.unpack('>I',correct_data_frames_missed))[0]
    val_err_data_missed= list(struct.unpack('>I',err_data_frames_missed))[0]
    Frame_count[file_timestamp].append([val_data_missed,val_err_data_missed])
	#print "----------done with missed .. now with actual data "
    correct_data_frames=header_and_correct_data_frames[data_file_header_byte_count+1:]
    data_index=0
    for idx in xrange(0,len(correct_data_frames)-DATA_STRUCT_SIZE ,DATA_STRUCT_SIZE ):	
        global file_timestamp
        frame=correct_data_frames[data_index:data_index+DATA_STRUCT_SIZE]
        offset,success,tsf= 8,-1,0
        header = frame[:offset]
        if success:
            Frame_count[file_timestamp][0][0] = Frame_count[file_timestamp][0][0]  +1
        else:
            print "success denied"                    
        data_index=data_index+DATA_STRUCT_SIZE

    data_index=0
    for idx in xrange(0,len(err_data_frames)-DATA_ERR_STRUCT_SIZE,DATA_ERR_STRUCT_SIZE ):	
        frame=err_data_frames[data_index:data_index+DATA_ERR_STRUCT_SIZE]
        offset,success,tsf= 8,-1,0
        header = frame[:offset]
        (version,pad,radiotap_len,present_flag)=struct.unpack('<BBHI',header)
        if success:
            Frame_count[file_timestamp][0][1] = Frame_count[file_timestamp][0][1]  +1
        else :
            print "success denied"                    
        data_index= data_index+DATA_ERR_STRUCT_SIZE

            
    #The following code block parses the mgmt files 
    val_beacon_missed= list(struct.unpack('>I',beacon_mgmt_frames_missed))[0]
    val_common_missed= list(struct.unpack('>I',common_mgmt_frames_missed))[0]
    val_err_mgmt_missed= list(struct.unpack('>I',err_mgmt_frames_missed))[0]
    Frame_count[file_timestamp].append([val_beacon_missed+val_common_missed,val_err_mgmt_missed])     
    #print "----------done with missed .. now with actual mgmt data "
    beacon_mgmt_frames=header_and_beacon_mgmt_frames[mgmt_file_header_byte_count+1:]
    mgmt_index=0
    for idx in xrange(0,len(beacon_mgmt_frames)-MGMT_BEACON_STRUCT_SIZE ,MGMT_BEACON_STRUCT_SIZE ):		
        global file_timestamp
        frame=beacon_mgmt_frames[mgmt_index:mgmt_index+MGMT_BEACON_STRUCT_SIZE]
        offset,success,tsf= 8,-1,0
        header = frame[:offset]
        if success :
            Frame_count[file_timestamp][1][0] = Frame_count[file_timestamp][1][0] + 1
        else :
            print "success denied"        
        mgmt_index=mgmt_index+MGMT_BEACON_STRUCT_SIZE
            
    mgmt_index=0
    for idx in xrange(0,len(common_mgmt_frames)-MGMT_COMMON_STRUCT_SIZE ,MGMT_COMMON_STRUCT_SIZE ):
        global file_timestamp	
        frame=common_mgmt_frames[mgmt_index:mgmt_index+MGMT_COMMON_STRUCT_SIZE]
        offset,success,tsf= 8, -1,0
        header = frame[:offset]
        if success :
            Frame_count[file_timestamp][1][0] = Frame_count[file_timestamp][1][0]  +1
        else:
            print "success denied"
        mgmt_index=mgmt_index+MGMT_COMMON_STRUCT_SIZE

    mgmt_index=0
    for idx in xrange(0,len(err_mgmt_frames)-MGMT_ERR_STRUCT_SIZE,MGMT_ERR_STRUCT_SIZE ):	
        global file_timestamp
        frame=err_mgmt_frames[mgmt_index:mgmt_index+MGMT_ERR_STRUCT_SIZE]
        offset,success,tsf= 8,-1,0
        header = frame[:offset]
        if success :
            Frame_count[file_timestamp][1][1] = Frame_count[file_timestamp][1][1]  +1
        else: 
            print "success denied"
        mgmt_index= mgmt_index+MGMT_ERR_STRUCT_SIZE
                
    #he following code block parses the ctrl files 
    val_ctrl_missed= list(struct.unpack('>I',correct_ctrl_frames_missed))[0]
    val_err_ctrl_missed= list(struct.unpack('>I',err_ctrl_frames_missed))[0]

    #print "----------done with missed .. now with actual ctrl data "
    Frame_count[file_timestamp].append([val_ctrl_missed,val_err_ctrl_missed])
    correct_ctrl_frames=header_and_correct_ctrl_frames[ctrl_file_header_byte_count+1:]
    ctrl_index=0
    for idx in xrange(0,len(correct_ctrl_frames)-CTRL_STRUCT_SIZE ,CTRL_STRUCT_SIZE ):			
        global file_timestamp
        frame=correct_ctrl_frames[ctrl_index:ctrl_index+CTRL_STRUCT_SIZE]
        offset,success,tsf= 8,-1,0
        header = frame[:offset]
        if success :
            Frame_count[file_timestamp][2][0] = Frame_count[file_timestamp][2][0]  +1
        else :
            print "success denied"
        ctrl_index=ctrl_index+CTRL_STRUCT_SIZE

    ctrl_index=0
    for idx in xrange(0,len(err_ctrl_frames)-CTRL_ERR_STRUCT_SIZE,CTRL_ERR_STRUCT_SIZE):			
        global file_timestamp
        frame=err_ctrl_frames[ctrl_index:ctrl_index+CTRL_ERR_STRUCT_SIZE]
        offset,success,tsf= 8,-1,0
        header = frame[:offset]
        (version,pad,radiotap_len,present_flag)=struct.unpack('<BBHI',header)
        if success:
            Frame_count[file_timestamp][2][1] = Frame_count[file_timestamp][2][1]  +1
        else :
            print "success denied"
        ctrl_index= ctrl_index+CTRL_ERR_STRUCT_SIZE

        
    file_counter +=1
    if file_counter %10 == 0:
        print file_counter

print "done; writing to a file "

f_fc= output_fc_filename
output_fc = open(f_fc, 'wb')
pickle.dump(Frame_count,output_fc )
output_fc.close()
for i in range(0,len(missing_files)):
	print missing_files[i]
print "number of files that can't be located ", len(missing_files)	
