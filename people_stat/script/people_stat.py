#!/usr/bin/env python
import rospy
from people_msgs.msg import People,Person
from nav_msgs.msg import Odometry as odom
import tf
import numpy as np

zero = 1e-10

class people_stat():
    def __init__(self):
        self.get_param()
        rospy.init_node('people_stat')

        # set up
        self.nzero = 1e-3
        self.listener = tf.TransformListener()
        self.publisher()

        self.wait_for_tf()


    def get_param(self):
        rospy.loginfo('get_param')
        self.max_people = rospy.get_param('max_people',15)
        # self.frame_id = rospy.get_param('camera_frame_id','openni_depth_frame')
        self.frame_id = rospy.get_param('camera_frame_id','map')
        self.people_topic = rospy.get_param('people_topic','people')
        # self.sensitive_dist = rospy.get_param('sensitive_dist',2.0)
        # self.minimum_vel = rospy.get_param('minimum_vel',2.0)
        self.change = rospy.get_param('change',0.05)
        self.dur_tf = rospy.get_param('dur_tf',2.0)
        self.dur_tw = rospy.get_param('dur_tw',0.1)

        self.threshold = rospy.get_param('vel_threshold',1.0)
        self.holding_time = rospy.get_param('holding_time',10.0)

    def publisher(self):
        self.pub = rospy.Publisher(self.people_topic,People,queue_size=10)

    def wait_for_tf(self):
        rospy.loginfo('start')
        self.rate = rospy.Rate(10)
        self.people_prev = {}

        self.last_times = np.array([rospy.Time(0)]*self.max_people)
        self.last_poses = np.array([Person()]*self.max_people)
        self.cam_poses = np.array([[0.00,0.00,0.00]]*self.max_people)
        rospy.loginfo(len(self.last_times))
        rospy.loginfo(len(self.last_poses))

        while not rospy.is_shutdown():

            people_cnt = 0

            # create msg
            people_msg = People()
            people_msg.header.stamp = rospy.Time.now()
            people_msg.header.frame_id = self.frame_id

            self.people_now = {}

            for i in range(1,self.max_people):
                try:
                    child = 'neck_'+str(i)
                    time = rospy.Time(0)

                    if rospy.Time.now().secs>=self.dur_tf:
                        starttf_time = rospy.Time.now()-rospy.Duration(self.dur_tf)
                    else:
                        starttf_time = rospy.Time(0)

                    # rospy.loginfo('%s %s'%(self.frame_id,child))

                    # (pose,qt) = self.listener.lookupTransform(self.frame_id,child,starttf_time)
                    (cam_pose,cam_qt) = self.listener.lookupTransform('openni_depth_frame',child,starttf_time)

                    miss = (abs(cam_pose[0]-self.cam_poses[i][0])<zero) or (abs(cam_pose[1]-self.cam_poses[i][1])<zero) \
                        or (abs(cam_pose[2]-self.cam_poses[i][2])<zero)

                    if miss:
                        # rospy.loginfo('{} {} {}'.format(child,cam_pose-self.cam_poses[i],zero))
                        if rospy.Time.now() - self.last_times[i] >rospy.Duration(self.holding_time):
                            self.cam_poses[i] = cam_pose
                            continue

                        people_msg.people.append(self.last_poses[i])
                        self.cam_poses[i] = cam_pose
                        continue
                    else:
                        self.cam_poses[i] = cam_pose
                        # rospy.loginfo('hi')
                    rospy.loginfo('----run {} {} {}'.format(child,cam_pose,self.cam_poses[i]))

                    (pose,qt) = self.listener.lookupTransform(self.frame_id,child,starttf_time)
                    (lin,ang) = self.listener.lookupTwist(self.frame_id,child,rospy.Time(0),rospy.Duration(self.dur_tw))

                    # rospy.loginfo('append')

                    person_msg = Person()
                    person_msg.name  = 'vel_%s'%(str(i)) #'vel_%s' % (child)
                    (person_msg.position.x,person_msg.position.y,person_msg.position.z) = pose

                    # velocity is too sensitive
                    # if np.linalg.norm(np.array(lin)-0) >= self.minimum_vel:
                        # (person_msg.velocity.x,person_msg.velocity.y,person_msg.velocity.z) = lin

                    if child in self.people_prev:
                        (person_msg.velocity.x,person_msg.velocity.y,person_msg.velocity.z) = \
                            (self.people_prev[child].velocity.x*(1-self.change)+self.change*lin[0], \
                            self.people_prev[child].velocity.y*(1-self.change)+self.change*lin[1], \
                            self.people_prev[child].velocity.z*(1-self.change)+self.change*lin[2])
                    else:
                        (person_msg.velocity.x,person_msg.velocity.y,person_msg.velocity.z) = \
                            (self.change*lin[0], \
                            self.change*lin[1], \
                            self.change*lin[2])

                    if np.linalg.norm(np.array(lin)-0) < self.threshold:
                        (person_msg.velocity.x,person_msg.velocity.y,person_msg.velocity.z) = (0,0,0)

                    self.people_now[child] = person_msg
                    people_msg.people.append(person_msg)

                    people_cnt += 1


                    self.last_times[i] = rospy.Time.now()
                    self.last_poses[i] = person_msg

                except (tf.LookupException, tf.ConnectivityException,tf.ExtrapolationException):
                    # rospy.loginfo('err')
                    if rospy.Time.now() - self.last_times[i] >rospy.Duration(self.holding_time):
                        continue

                    people_msg.people.append(self.last_poses[i])



            self.people_prev = self.people_now

            # if people_cnt <= 0:
            #     continue

            # rospy.loginfo('publish di wa')
            # rospy.loginfo(people_msg)
            self.prev_people = people_msg

            # rospy.loginfo('wat')  

            self.pub.publish(people_msg)

            self.rate.sleep()


    def send_vel(self,msg):
        rospy.loginfo('calculate_vel')

if __name__ == '__main__':
    ps = people_stat()
