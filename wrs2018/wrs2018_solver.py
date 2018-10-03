#!/usr/bin/python

import cv2
import numpy as np
import roslib
import rospy
import yodpy
from rovi.msg import Floats
from rospy.numpy_msg import numpy_msg
from std_msgs.msg import Bool
from std_msgs.msg import String
from std_srvs.srv import Trigger,TriggerRequest
from sensor_msgs.msg import PointCloud
from geometry_msgs.msg import Point32
from geometry_msgs.msg import Point
from geometry_msgs.msg import Transform
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../script'))
import tflib

Tolerance=0.001
Rejection=2.5

def P0():
  return np.array([]).reshape((-1,3))

def np2F(d):  #numpy to Floats
  f=Floats()
  f.data=np.ravel(d)
  return f

def np2PC(d):  #numpy to PointCloud
  pc=PointCloud()
  pc.header.frame_id='hand' # TODO?
  f=np.ravel(d)
  for e in f.reshape((-1,3)):
    p=Point32()
    p.x=e[0]
    p.y=e[1]
    p.z=e[2]
    pc.points.append(p)
  return pc

def prepare_model(stl_file):
  global model, is_prepared
  result = yodpy.train3D(stl_file, relSamplingDistance = 0.03)
  retcode = result[0]
  model = result[1]
  print('train3D retcode=', retcode)
  print('train3D model size=', len(model))
  print('train3D model=', model)
  if retcode == 0:
    is_prepared = True
  return

def cb_ps(msg): #callback of ps_floats
  #global model

  print "cb_ps called!"

  if not is_prepared:
    print "ERROR: prepare_model() is NOT done. ignore this ps_floats."
    pub_Y1.publish(False)
    return



  pub_Y1.publish(True)
  # TODO recognition
  result = yodpy.loadPLY("/tmp/test.ply", scale="m")
  retcode = result[0]
  scene = result[1]
  print('loadPLY retcode=',retcode)
  print('loadPLY scene=',scene)

  if retcode != 0:
    print "ERROR: loadPLY() failed. ignore this ps_floats."
    pub_Y1.publish(False)
    return

  pub_Y1.publish(True)
  #### TODO
  """
  # TODO
  #result = yodpy.match3D(scene)
  result = yodpy.match3D(scene,relSamplingDistance=0.03,keyPointFraction=0.1,minScore=0.11)
  #result = yodpy.match3D(scene,relSamplingDistance=0.03,keyPointFraction=0.05,minScore=0.11)
  #result = yodpy.match3D(scene,relSamplingDistance=0.05,keyPointFraction=0.1,minScore=0.11)

  retcode = result[0]
  transforms = result[1]
  quats = result[2]
  matchRates = result[3]
  print('match3D retcode=',retcode)
  print('match3D transforms size=',len(transforms))
  print('match3D quats size=',len(quats))
  print('match3D matchRates size=',len(matchRates))

  print('match3D transforms type=',type(transforms))
  print('match3D quats type=',type(quats))
  print('match3D matchRates type=',type(matchRates))

  for quat in quats:
    print('match3D quat type=',type(quat))
    print('match3D quat=',quat)

  for matchRate in matchRates:
    print('match3D matchRate type=',type(matchRate))
    print('match3D matchRate=',matchRate)
  """


  #### TODO

  global bTmLat, mTc, scnPn, scnMk
  #mTb=np.linalg.inv(bTmLat)
  P=np.reshape(msg.data,(-1,3))
  n,m=P.shape
  #P=voxel(P)
  print "PointCloud In:",n
  print "PC(camera)",P
  n,m=P.shape
  print "PointCloud Out:",n
  P=np.vstack((P.T,np.ones((1,n))))
  P=np.dot(bTm[:3],np.dot(mTc,P)).T
  print "P2",P # now unit is mm
  print P.shape
  if (not np.isnan(xmin)):
    W = np.where(P.T[0] >= xmin)
    P=P[W[len(W)-1]]
  if (not np.isnan(xmax)):
    W = np.where(P.T[0] <= xmax)
    P=P[W[len(W)-1]]
  if (not np.isnan(ymin)):
    W = np.where(P.T[1] >= ymin)
    P=P[W[len(W)-1]]
  if (not np.isnan(ymax)):
    W = np.where(P.T[1] <= ymax)
    P=P[W[len(W)-1]]
  if (not np.isnan(zmin)):
    W = np.where(P.T[2] >= zmin)
    P=P[W[len(W)-1]]
  if (not np.isnan(zmax)):
    W = np.where(P.T[2] <= zmax)
    P=P[W[len(W)-1]]
  print "where",P
  n,m=P.shape
  print P.shape
  print "PC",P
  P=P.reshape((-1,3))
  scnPn=np.vstack((scnPn,P))
  pub_scf.publish(np2F(scnPn))
  pub_sck.publish(np2PC(scnPn))
  return

"""
  scnPn=np.vstack((scnPn,P))
  pub_scf.publish(np2F(scnPn))
  P=np.dot(mTb[:3],np.dot(bTc,P)).T
  print "Marker",P
  scnMk=np.vstack((scnMk,P))
  pc=np2PC(scnMk)
  pub_sck.publish(pc)
"""

def cb_X0(f):
  global scnPn,scnMk
  print "X0:scene reset"
  scnPn=P0()
  scnMk=P0()
  pub_scf.publish(np2F(scnPn))
  pub_sck.publish(np2PC(scnMk))
  return

def cb_X1(f):
  global bTm,bTmLat
  bTmLat=np.copy(bTm)
  print "bTm latched",bTmLat
  genpc=None
  try:
    genpc=rospy.ServiceProxy('/rovi/pshift_genpc',Trigger)
    req=TriggerRequest()
    genpc(req)      #will continue to callback cb_ps
  except rospy.ServiceException, e:
    print 'Genpc proxy failed:'+e
    pub_Y1.publish(False)
  return

def cb_X2(f):
  global scnPn,scnMk,modPn
  print "X2:ICP",modPn.shape,scnPn.shape
  icp=cv2.ppf_match_3d_ICP(100,Tolerance,Rejection,8)
  mp=modPn.astype(np.float32)
  sp=scnPn.astype(np.float32)
  ret,residu,RT=icp.registerModelToScene(mp,sp)
  print "Residue=",residu
  print RT
  pub_tf.publish(tflib.fromRT(RT))
  TR=np.linalg.inv(RT)
  P=np.vstack((scnPn.T,np.ones((1,len(scnPn)))))
  scnPn=np.dot(TR[:3],P).T
  pub_scf.publish(np2F(scnPn))

  #sprintf_s(buf, sizeof(buf), "OK\x0d(%.3f,%.3f,%.3f,%.3f,%.3f,%.3f)(7,0)\x0d", rpos.x, rpos.y, rpos.z, rpos.rx, rpos.ry, rpos.rz);
  #sprintf_s(buf, sizeof(buf), "NG\x0d");
  #pub_Y2.publish(True)

  return

def cb_X3(f):
  pub_scf.publish(np2F(scnPn))
  pub_sck.publish(np2PC(scnMk))
  return

def cb_tf(tf):
  global bTm
  bTm=tflib.toRT(tf)
  return

########################################################

rospy.init_node("solver",anonymous=True)
###Input topics
rospy.Subscriber("/robot/tf",Transform,cb_tf)
rospy.Subscriber("/rovi/ps_floats",numpy_msg(Floats),cb_ps)
rospy.Subscriber("/solver/X0",Bool,cb_X0)  #Clear scene
rospy.Subscriber("/solver/X1",Bool,cb_X1)  #Capture position of marker and robot
rospy.Subscriber("/solver/X2",Bool,cb_X2)  #Calc transform
rospy.Subscriber("/solver/X3",Bool,cb_X3)  #redraw

###Output topics
pub_tf=rospy.Publisher("/solver/tf",Transform,queue_size=1)
pub_scf=rospy.Publisher("/scene/floats",numpy_msg(Floats),queue_size=1)
pub_sck=rospy.Publisher("/scene/marker",PointCloud,queue_size=1)
pub_Y1=rospy.Publisher('/solver/Y1',Bool,queue_size=1)    #X1 done
pub_Y2=rospy.Publisher('/solver/Y2',Bool,queue_size=1)    #X2 done

###Transform
mTc=tflib.toRT(tflib.dict2tf(rospy.get_param('/robot/calib/mTc')))  # arM tip To Camera
print "mTc=", mTc
bTmLat=np.eye(4).astype(float)  #robot RT when captured
bTm=np.eye(4).astype(float) 

###Globals
scnPn=P0()  #Scene points
scnMk=P0()  #Scene Marker points
modPn=P0()  #Model points
is_prepared = False

xmin = float(rospy.get_param('/volume_of_interest/xmin'))
xmax = float(rospy.get_param('/volume_of_interest/xmax'))
ymin = float(rospy.get_param('/volume_of_interest/ymin'))
ymax = float(rospy.get_param('/volume_of_interest/ymax'))
zmin = float(rospy.get_param('/volume_of_interest/zmin'))
zmax = float(rospy.get_param('/volume_of_interest/zmax'))
print "xmin=", xmin, "xmax=", xmax, "ymin=", ymin, "ymax=", ymax, "zmin=", zmin, "zmax=", zmax

try:
  prepare_model(os.environ['ROVI_PATH'] + '/wrs2018/model/Gear.stl')
  rospy.spin()
except KeyboardInterrupt:
  print "Shutting down"