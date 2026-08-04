import sys
import cv2


def build_pipeline(sensor_id):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        "video/x-raw(memory:NVMM), width=1280, height=720, "
        "framerate=30/1, format=NV12 ! "
        "nvvidconv flip-method=0 ! "
        "video/x-raw, width=640, height=480, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink drop=true max-buffers=1"
    )


def main():
    sensor_id = 0
    if len(sys.argv) > 1:
        try:
            sensor_id = int(sys.argv[1])
        except ValueError:
            sensor_id = 0

    pipeline = build_pipeline(sensor_id)
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        sys.stderr.write("CAMERA: FAILED\n")
        sys.stderr.flush()
        sys.exit(1)

    out = sys.stdout.buffer
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 70]

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                sys.stderr.write("CAMERA: FRAME_FAIL\n")
                sys.stderr.flush()
                break

            ok, jpg = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                continue

            data = jpg.tobytes()
            out.write(b"\xff\xd8\xff")
            out.write(len(data).to_bytes(4, "big"))
            out.write(data)
            out.flush()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        cap.release()


if __name__ == "__main__":
    main()
