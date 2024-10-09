import cv2
import mediapipe as mp
import numpy as np

# 初始化mediapipe的面部检测
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# 捕捉摄像头视频流
cap = cv2.VideoCapture(0)

# 眼睛相关的关键点索引
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

# 显示注视点的屏幕坐标（模拟屏幕中央的光点）
screen_center_x = 1080  # 你可以根据屏幕大小进行调整
screen_center_y = 1080

def detect_pupil(eye_region):
    """瞳孔检测，找到黑色区域"""
    gray_eye = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
    _, threshold_eye = cv2.threshold(gray_eye, 30, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(threshold_eye, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) > 0:
        largest_contour = max(contours, key=cv2.contourArea)
        (x, y, w, h) = cv2.boundingRect(largest_contour)
        return x + w // 2, y + h // 2
    return None

def get_eye_region(landmarks, eye_indices, frame):
    """得到眼睛区域坐标并提取眼睛图像"""
    h, w, _ = frame.shape
    eye_points = [(int(landmarks[point].x * w), int(landmarks[point].y * h)) for point in eye_indices]
    return np.array(eye_points, np.int32)

def calculate_gaze(pupil_position, eye_region):
    """基于瞳孔和眼睛区域计算注视点（简单的推测，需校准）"""
    eye_center = np.mean(eye_region, axis=0).astype(int)
    if pupil_position is not None:
        # 简单估计：如果瞳孔偏向眼睛中心的左侧，推测注视点偏左；同理，偏右则注视右侧
        if pupil_position[0] < eye_center[0]:  # 瞳孔偏左
            return screen_center_x - 100, screen_center_y
        elif pupil_position[0] > eye_center[0]:  # 瞳孔偏右
            return screen_center_x + 100, screen_center_y
    return screen_center_x, screen_center_y  # 默认返回屏幕中心

def gaze_tracking(landmarks, frame):
    """基于瞳孔位置和眼睛位置来计算注视方向，并显示红光点"""
    left_eye_region = get_eye_region(landmarks, LEFT_EYE_INDICES, frame)
    right_eye_region = get_eye_region(landmarks, RIGHT_EYE_INDICES, frame)

    # 提取左眼和右眼区域图像
    left_eye_frame = frame[min(left_eye_region[:, 1]):max(left_eye_region[:, 1]),
                           min(left_eye_region[:, 0]):max(left_eye_region[:, 0])]
    right_eye_frame = frame[min(right_eye_region[:, 1]):max(right_eye_region[:, 1]),
                            min(right_eye_region[:, 0]):max(right_eye_region[:, 0])]

    left_pupil = detect_pupil(left_eye_frame)
    right_pupil = detect_pupil(right_eye_frame)

    # 计算注视点
    left_gaze = calculate_gaze(left_pupil, left_eye_region)
    right_gaze = calculate_gaze(right_pupil, right_eye_region)

    # 平均左右眼的注视点
    gaze_x = int((left_gaze[0] + right_gaze[0]) / 2)
    gaze_y = int((left_gaze[1] + right_gaze[1]) / 2)

    # 在注视点位置绘制红色光点
    cv2.circle(frame, (gaze_x, gaze_y), 20, (0, 0, 255), -1)

    return frame

with mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5) as face_mesh:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # 翻转图像，避免镜像问题
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 处理图像并获得面部网格
        result = face_mesh.process(rgb_frame)

        if result.multi_face_landmarks:
            for face_landmarks in result.multi_face_landmarks:
                frame = gaze_tracking(face_landmarks.landmark, frame)
                # 绘制面部网格（可选）
                mp_drawing.draw_landmarks(frame, face_landmarks, mp_face_mesh.FACEMESH_CONTOURS)

        cv2.imshow("眼球追踪 - 注视点显示", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
