import subprocess, os, time, threading
from datetime import datetime

class satdump_receiver:
    def __init__(self, sample_rate=2_400_000, gain=35):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(base_dir, "transmissions")
        self.sample_rate = sample_rate
        self.gain = gain
        self.recording_process = None
        self.current_satellite = None
        self.is_recording = False

        os.makedirs(self.output_dir, exist_ok=True)

    def list_satellites(self):
        """query satdump for list of available decoders"""
        try:
            cmd = ["satdump", "--list"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            sats = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return sats
        except Exception as e:
            return [f"error listing satellites: {e}"]

    def start_recording(self, sat_name, center_freq_hz, duration_sec, rtl_device="0"):
        """start rf recording for specified satellite"""
        if self.is_recording:
            raise RuntimeError("already recording")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        outfile = os.path.join(self.output_dir, f"{sat_name}_{timestamp}.iq")
        self.current_satellite = sat_name
        cmd = [
            "satdump",
            "recv",
            sat_name,
            "--samplerate", str(self.sample_rate),
            "--gain", str(self.gain),
            "--freq", str(center_freq_hz),
            "--device", rtl_device,
            "--output", outfile
        ]

        self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.is_recording = True

        def auto_stop():
            time.sleep(duration_sec)
            self.stop_recording()

        threading.Thread(target=auto_stop, daemon=True).start()
        return outfile

    def stop_recording(self):
        """stop recording gracefully"""
        if not self.is_recording:
            return False
        self.recording_process.terminate()
        self.recording_process.wait(timeout=5)
        self.is_recording = False
        return True

    def decode_recording(self, iq_file, sat_name):
        """decode iq data using satdump api"""
        out_dir = os.path.splitext(iq_file)[0] + "_decoded"
        os.makedirs(out_dir, exist_ok=True)
        cmd = [
            "satdump",
            "decode",
            sat_name,
            iq_file,
            "--outdir", out_dir
        ]
        subprocess.run(cmd, check=True)
        return out_dir

    def find_latest_image(self, decoded_dir):
        """scan decoded folder for latest image file"""
        images = []
        for root, _, files in os.walk(decoded_dir):
            for f in files:
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    images.append(os.path.join(root, f))
        if not images:
            return None
        images.sort(key=os.path.getmtime, reverse=True)
        return images[0]
