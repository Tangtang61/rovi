#include <ros/ros.h>
#include <std_srvs/Trigger.h>
#include <std_msgs/Float64.h>
#include <opencv2/opencv.hpp>
#include <cv_bridge/cv_bridge.h>
#include "rovi/ImageFilter.h"
#include <iostream>

ros::NodeHandle *nh;
ros::Publisher pub;

cv::Mat rmapx, rmapy;

int reload()
{
  std::vector<double> D;
  nh->getParam("remap/D", D);
  if (D.size() != 5)
  {
    ROS_ERROR("Param D NG");
    return -1;
  }
  std::vector<double> K;
  nh->getParam("remap/K", K);
  if (K.size() != 9)
  {
    ROS_ERROR("Param K NG");
    return -1;
  }
  std::vector<double> R;
  nh->getParam("remap/R", R);
  if (R.size() != 9)
  {
    ROS_ERROR("Param R NG");
    return -1;
  }
  std::vector<double> P;
  nh->getParam("remap/P", P);
  if (P.size() != 12)
  {
    ROS_ERROR("Param P NG");
    return -1;
  }
  std::vector<double> ncam;
  cv::Mat Pro(P), nCam, nRot, nTrans;
  cv::OutputArray oCam(nCam), oRot(nRot), oTrans(nTrans);
  cv::decomposeProjectionMatrix(Pro.reshape(1, 3), oCam, oRot, oTrans);
  ncam.assign(nCam.begin<double>(), nCam.end<double>());
  nh->setParam("remap/Kn", ncam);
  int width = 0, height = 0;
  nh->getParam("remap/width", width);
  nh->getParam("remap/height", height);
  cv::Size imgsz(width, height);
  if (imgsz.area() == 0)
  {
    ROS_ERROR("Size NG");
    return -1;
  }
  cv::Mat Cam(K), Rot(R);
  cv::initUndistortRectifyMap(Cam.reshape(1, 3), D, Rot.reshape(1, 3), nCam, imgsz, CV_32FC1, rmapx, rmapy);
  ROS_INFO("remap:reload ok");
  return 0;
}

bool remap(rovi::ImageFilter::Request &req, rovi::ImageFilter::Response &res)
{
  ros::Time t0 = ros::Time::now();
  cv_bridge::CvImagePtr cv_ptr;
  try
  {
    cv_ptr = cv_bridge::toCvCopy(req.img, sensor_msgs::image_encodings::MONO8);
  }
  catch (cv_bridge::Exception& e)
  {
    ROS_ERROR("remap:cv_bridge:exception: %s", e.what());
    return false;
  }
  cv::Mat result;
  cv::remap(cv_ptr->image, result, rmapx, rmapy, cv::INTER_LINEAR, cv::BORDER_TRANSPARENT, 0);
  cv_ptr->image = result;
  cv_ptr->toImageMsg(res.img);
  std_msgs::Float64 tat;
  tat.data = (ros::Time::now() - t0).toSec();
  pub.publish(tat);
  return true;
}

int main(int argc, char **argv)
{
  ros::init(argc, argv, "remap_node");
  ros::NodeHandle n;
  nh = &n;
  if(reload()<0) return 1;
  ros::ServiceServer svc1 = n.advertiseService("remap", remap);
  pub = n.advertise<std_msgs::Float64>("remap/tat", 1);
  ros::spin();
  return 0;
}
