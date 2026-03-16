import cv2
import time
import numpy as np
import mediapipe as mp

from argus.driver import CanbusDriver

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# cols, rows = 640, 480

base_options = python.BaseOptions(
    model_asset_path="models/blaze_face_short_range.tflite"
)
options = vision.FaceDetectorOptions(base_options=base_options)
detector = vision.FaceDetector.create_from_options(options)


tty = "/dev/tty.usbmodem206B358043331"

pan_servo_id = 0
pan_angle = 90.0
tilt_servo_id = 1
tilt_angle = 110.0


cap = cv2.VideoCapture(0)
cols = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
rows = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
offset = cols // 60

driver = CanbusDriver(interface="slcan", channel=tty, bitrate=500000)

driver.move_pwm_servo(pan_servo_id, int(pan_angle))
driver.move_pwm_servo(tilt_servo_id, int(tilt_angle))

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Convert the frame to RGB as required by MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # Run face detection
    detection_result = detector.detect(mp_image)

    # Draw face bounding boxes
    if detection_result.detections:
        for detection in detection_result.detections:
            bbox = detection.bounding_box
            x, y, w, h = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (x + w // 2, y + h // 2), 5, (0, 255, 0), -1)

            face_center_x = x + w // 2
            face_center_y = y + h // 2

            pan_error = face_center_x - cols // 2
            tilt_error = face_center_y - rows // 2

            if pan_error > offset:
                pan_angle -= 1.0
            if pan_error < -offset:
                pan_angle += 1.0
            if pan_error < -offset:
                pan_angle += 1.0

            if pan_angle > 0 and pan_angle < 180:
                driver.move_pwm_servo(pan_servo_id, int(pan_angle))

            if tilt_error > offset:
                tilt_angle += 1.0
            if tilt_error < -offset:
                tilt_angle -= 1.0

            cv2.putText(
                frame,
                f"Pan: {int(pan_angle)}  Tilt: {int(tilt_angle)}, offset: {offset}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            if tilt_angle > 0 and tilt_angle < 135:
                driver.move_pwm_servo(tilt_servo_id, int(tilt_angle))

    time.sleep(1 / 30)

    cv2.imshow("Face Tracking", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
        break

cap.release()
cv2.destroyAllWindows()
