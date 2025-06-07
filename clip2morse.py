'''
Name: clip2morse
Author: Cooper Wiegand
https://github.com/Cooperw/clip2morse


MIT License

Copyright (c) 2025 Cooper Wiegand

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import cv2
import numpy as np
import os
import re
import argparse
from itertools import groupby
from sklearn.cluster import KMeans

# === Morse Dictionary ===
# You can also add in custom "common morse" like SOS
MORSE_DICT = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
    "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
    "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
    "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y",
    "--..": "Z", "-----": "0", ".----": "1", "..---": "2", "...--": "3",
    "....-": "4", ".....": "5", "-....": "6", "--...": "7", "---..": "8",
    "----.": "9", "...---...": "SOS"
}

OUTPUT_PATH = "output/raw_net_color.txt"
RGB_TOLERANCE = 90 # this value has to do with ambient light changes during the clip

def get_changed_pixel_average(base_frame, current_frame, tolerance):
    diff = cv2.absdiff(base_frame, current_frame)
    mask = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY) > tolerance
    mask_3ch = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
    changed_pixels = current_frame[mask_3ch].reshape(-1, 3)
    count = changed_pixels.shape[0]
    if count == 0:
        return (0, 0, 0, 0)
    avg_rgb = np.mean(changed_pixels, axis=0).astype(int)
    return (*avg_rgb, count)

def extract_frames(video_path):
    os.makedirs("output", exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[ERROR] Error opening video file:", video_path)
        return False

    ret, start_frame = cap.read()
    if not ret:
        print("[ERROR] Couldn't read the first frame.")
        return False

    start_frame = cv2.resize(start_frame, (320, 240))

    with open(OUTPUT_PATH, "w") as out_file:
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (320, 240))
            r, g, b, count = get_changed_pixel_average(start_frame, frame, RGB_TOLERANCE)
            out_file.write(f"{frame_idx}: {r} {g} {b} ({count})\n")
            frame_idx += 1

    cap.release()
    print(f"Frame data saved to {OUTPUT_PATH}")
    return True

def load_frames(path, brightness_threshold):
    binary_list = []
    with open(path) as f:
        for line in f:
            match = re.search(r"\d+: (\d+) (\d+) (\d+)", line)
            if not match:
                continue
            r, g, b = map(int, match.groups())
            avg = (r + g + b) / 3
            binary_list.append(avg >= brightness_threshold)
    return binary_list

def group_frames(binary_list):
    return [(key, sum(1 for _ in group)) for key, group in groupby(binary_list)]

def cluster_lengths(lengths, n_clusters=2):
    if not lengths:
        return [], []
    data = np.array(lengths).reshape(-1, 1)
    kmeans = KMeans(n_clusters=n_clusters, n_init='auto').fit(data)
    centers = kmeans.cluster_centers_.flatten()
    labels = kmeans.predict(data)
    return list(labels), centers

def decode_morse(groups, brightness_threshold):
    on_groups = [(i, l) for i, (is_on, l) in enumerate(groups) if is_on]
    off_groups = [(i, l) for i, (is_on, l) in enumerate(groups) if not is_on]

    on_lengths = [l for _, l in on_groups]
    off_lengths = [l for _, l in off_groups]

    on_labels, on_centers = cluster_lengths(on_lengths, 2)
    on_sorted = np.argsort(on_centers.copy())
    if len(on_sorted) == 0:
        print(f"[ERROR] Unable to locate any pixels that are above threshold of {brightness_threshold}. Consider adjusting the threshold parameter with --threshold / -t .")
        exit(1)
    dot_label = int(on_sorted[0])
    # dash_label = int(on_sorted[1]) # we dont use this currently

    off_labels, off_centers = cluster_lengths(off_lengths, 3)
    sorted_indices = np.argsort(off_centers.copy())
    gap_type = {
        int(sorted_indices[0]): "intra",
        int(sorted_indices[1]): "letter",
        int(sorted_indices[2]): "word"
    }

    # Debug clustering
    # print("ON centers (dot/dash):", on_centers)
    # print("OFF centers (gap types):", off_centers)
    # print("Gap type mapping:", gap_type)

    morse = []
    current_symbol = ""

    on_idx = 0
    off_idx = 0

    for is_on, length in groups:
        if is_on:
            label = on_labels[on_idx]
            on_idx += 1
            current_symbol += "." if label == dot_label else "-"
        else:
            label = off_labels[off_idx]
            off_idx += 1
            kind = gap_type[label]
            if kind == "word":
                if current_symbol:
                    morse.append(current_symbol)
                    current_symbol = ""
                morse.append("/")
            elif kind == "letter":
                if current_symbol:
                    morse.append(current_symbol)
                    current_symbol = ""

    if current_symbol:
        morse.append(current_symbol)

    return " ".join(morse)

def morse_to_text(morse_code):
    words = []
    current_word = []
    for symbol in morse_code.split():
        if symbol == "/":
            if current_word:
                words.append("".join(current_word))
                current_word = []
        else:
            current_word.append(MORSE_DICT.get(symbol, "?"))
    if current_word:
        words.append("".join(current_word))
    return " ".join(words)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a light-based Morse video clip.")
    parser.add_argument("-c", "--clip", type=str, required=True, help="Path to the video file (e.g. sample.mov / sample.mp4)")
    parser.add_argument("-t", "--threshold", type=int, default=245, help="Brightness threshold for ON (default: 245)")
    args = parser.parse_args()

    if extract_frames(args.clip):
        signal = load_frames(OUTPUT_PATH, args.threshold)
        grouped = group_frames(signal)
        morse = decode_morse(grouped, args.threshold)

        print("\nMorse Code:")
        print(morse)
        print("\nDecoded Text:")
        print(morse_to_text(morse))
