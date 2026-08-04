import cv2

status = True
def camtest(stop_event):
    global status
    pipeline = (
        "nvarguscamerasrc sensor-id=0 ! "
        "video/x-raw(memory:NVMM), width=1280, height=720,"
        "framerate=30/1, format=NV12 ! "
        "nvvidconv flip-method=0 ! "
        "video/x-raw, width=640, height=480, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink drop=true max-buffers=1"
    )
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("FAILED")
        status = False
        exit()


    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print("FAILED")
            status = False
            break

        cv2.imshow("Jetson Nano CSI Camera 1", frame)

        if cv2.waitKey(1) == ord('q'):
            break


    cap.release()
    cv2.destroyAllWindows()