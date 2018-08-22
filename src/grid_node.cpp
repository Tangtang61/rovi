#include <ros/ros.h>
#include <std_msgs/Empty.h>
#include <opencv2/opencv.hpp>
#include <cv_bridge/cv_bridge.h>
#include <geometry_msgs/Point.h>
#include <geometry_msgs/Transform.h>
#include "rovi/ImageFilter.h"
#include "CircleCalibBoard.h"

CircleCalibBoard cboard;
ros::NodeHandle *nh;
std::string paramK("gridboard/K");
static std::vector<double> kvec;
static ros::Publisher *pub1, *pub2;

void solve(sensor_msgs::Image src){
  geometry_msgs::Transform tf;
  cv_bridge::CvImagePtr cv_ptr1;
  try{
    cv_ptr1 = cv_bridge::toCvCopy(src, sensor_msgs::image_encodings::MONO8);
  }
  catch(cv_bridge::Exception& e){
    ROS_ERROR("get_grids:cv_bridge:exception: %s", e.what());
    pub2->publish(tf);
    return;
  }
  std::vector<cv::Point2f> imagePoints;
  cv::Mat mat;
  int cbres=cboard.scan(cv_ptr1->image, imagePoints, &mat);
  sensor_msgs::Image img;
  cv_ptr1->image=mat;
  cv_ptr1->encoding="bgr8";
  cv_ptr1->toImageMsg(img);
  pub1->publish(img);
  if(cbres){
    ROS_WARN("CircleCalibBoard::scan:failed:");
    pub2->publish(tf);
    return;
  }
  std::vector<cv::Point3f> model;
  std::vector<cv::Point2f> scene;
  geometry_msgs::Point p;
  p.z = 0;
  for (int i = 0; i < imagePoints.size(); i++){
    if (imagePoints[i].x == FLT_MAX || imagePoints[i].y == FLT_MAX){
      p.z = -1; // recognition failed
    }
    else{
      p.z = 0;
    }
    p.x = imagePoints[i].x;
    p.y = imagePoints[i].y;
    if (p.z < 0){
      continue;
    }
    cv::Point3f pm(cboard.get_3d_position(i));
    cv::Point2f ps(p.x, p.y);
    model.push_back(pm);
    scene.push_back(ps);
  }

  cv::Mat kmat(kvec);
  cv::Mat dmat = cv::Mat::zeros(5, 1, cv::DataType<float>::type); // No distortion
  cv::Mat rmat(3, 1, cv::DataType<double>::type);
  cv::Mat tmat(3, 1, cv::DataType<double>::type);
  cv::OutputArray oRmat(rmat), oTmat(tmat);
  cv::solvePnP(model, scene, kmat.reshape(1, 3), dmat, oRmat, oTmat);
  float rx = rmat.at<double>(0, 0);
  float ry = rmat.at<double>(1, 0);
  float rz = rmat.at<double>(2, 0);
  float rw = sqrt(rx * rx + ry * ry + rz * rz);
  tf.translation.x = tmat.at<double>(0, 0);
  tf.translation.y = tmat.at<double>(1, 0);
  tf.translation.z = tmat.at<double>(2, 0);
  tf.rotation.x = rw > 0 ? sin(rw / 2) * rx / rw : rx;
  tf.rotation.y = rw > 0 ? sin(rw / 2) * ry / rw : ry;
  tf.rotation.z = rw > 0 ? sin(rw / 2) * rz / rw : rz;
  tf.rotation.w = cos(rw / 2);
  pub2->publish(tf);
}

void reload(std_msgs::Empty e)
{
  for (std::map<std::string, double>::iterator itr = cboard.para.begin(); itr != cboard.para.end(); ++itr)
  {
    std::string pname("gridboard/");
    pname += itr->first;
    if (nh->hasParam(pname))
    {
      nh->getParam(pname, itr->second);
    }
  }
  cboard.init();
  if (! nh->getParam(paramK.c_str(), kvec))
  {
    ROS_ERROR("GetGrid::paramer \"K\" not found");
    return;
  }
}

int main(int argc, char **argv)
{
  if (argc >= 2)
  {
    paramK = argv[1];
    std::cout << "K=" << paramK << "\n";
  }
  ros::init(argc, argv, "grid_node");
  ros::NodeHandle n;
  nh = &n;
  cboard.para["bin_type"] = 1;

  n.subscribe("gridboard/image_in", 1, solve);
  n.subscribe("gridboard/X0", 1, reload);
  std_msgs::Empty msg;
  reload(msg);
  ros::Publisher p1 = n.advertise<sensor_msgs::Image>("gridboard/image_out", 1);
  pub1 = &p1;
  ros::Publisher p2 = n.advertise<geometry_msgs::Transform>("gridboard/tf", 1);
  pub2 = &p2;
  ros::spin();
  return 0;
}
