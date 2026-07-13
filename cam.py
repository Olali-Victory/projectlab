import cv2


def camtest(stop_event):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("FAILED")
        exit()

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print("FAILED 2")
            break

        cv2.imshow("Jetson Nano USB Camera", frame)

        if cv2.waitKey(1) == ord('q'):
            break


    cap.release()
    cv2.destroyAllWindows()