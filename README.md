# Welcome to **clip2morse**
A simple tool used to decode visual, light-based Morse video clips.  
Useful in CTFs, security research, and signal analysis where information is encoded using flashes of light.

`clip2morse` processes a video file, extracts frame-by-frame light changes, classifies them into Morse code, and outputs the decoded message.

#### Demo Video -> [TBD](https://www.britannica.com/dictionary/TBD)

## Sections
1. [Quick Start](#quick-start)
2. [Troubleshooting](#troubleshooting)
3. [General Algorithm](#general-algorithm)
4. [Design Challenges](#design-challenges)
5. [Resource Links](#resource-links)

## Quick Start

### Ensure you have python and venv
```bash
# For apt-based systems
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

### Construct venv and install dependencies
```bash
# Create a virtual environment in the current directory
python3 -m venv venv

# Activate the environment
source venv/bin/activate
```
```bash
# Install dependencies (in venv)
# Note: This took a while to install all of the scikit stuff
pip install -r requirements.txt
```

### Sample Clips
I have included some sample clips for your decoding pleasure
```
./clips
├── sample_1_SOS_SOS.mov                    # Real-World recording (SOS)
├── sample_1_SOS_SOS_crop.mov               # Ideal clip (SOS)
├── sample_2_HACK_THE_PLANET.mov            # Real-World recording (HACK THE PLANET)
├── sample_2_HACK_THE_PLANET_crop.mov       # Ideal clip (HACK THE PLANET)
```

### Sample Decodings => [See CyberChef for more](https://gchq.github.io/CyberChef/#recipe=To_Morse_Code('-/.','Space','Forward%20slash')From_Morse_Code('Space','Forward%20slash'/disabled)&input=U09TIFNPUw&ieol=CRLF)
```
SOS SOS
... --- ... / ... --- ...

HACK THE PLANET
.... .- -.-. -.- / - .... . / .--. .-.. .- -. . -
```

### How to Run
```bash
# usage: clip2morse.py [-h] -c CLIP [-t THRESHOLD]
$> python clip2morse.py --clip ./clips/sample_1_SOS_SOS_crop.mov
Frame data saved to output/raw_net_color.txt

Morse Code:
/ ... --- ... / ... --- ...

Decoded Text:
SOS SOS
```

## Troubleshooting

Are you having issues with decoding your signal? Take a look at some common issues & fixes.

### Thresholds
You should always crop down the clip if you can to "filter" out background "info". For some clips, changes in the background that are not related to the morse signal may cause interference. What if you moved the camera around too much during your recording? What if the signal is red instead of white? Introducing `Threshold`!

#### Step 1: Run a basic `clip2morse.py` to generate `./output/raw_net_color.txt`
```bash
# an example of when we discovered no pixels that meet our "default threshold"
$> python clip2morse.py --clip ./clips/sample_1_SOS_SOS.mov
Frame data saved to output/raw_net_color.txt
[ERROR] Unable to locate any pixels that are above threshold of 245. Consider adjusting the threshold parameter with --threshold / -t .
```

#### Step 2: Let's take a look at `output/raw_net_color.txt`
```bash
# here we can see that there are some noticable "chuncks" of colors
# see how frames 35-39 have a much higher number of pixels changed comparred to our carrier frame?
# frames 35-39 are "near-white" and well above 200 for each RGB values compared to other frames
# frame: R G B (num pixels changed)
32: 181 187 196 (327)
33: 180 187 195 (344)
34: 181 187 196 (363)
35: 238 233 238 (4373)  #
36: 237 232 236 (4347)  #
37: 236 231 235 (4330)  #
38: 225 221 226 (2488)  #
39: 164 171 179 (352)
40: 164 171 179 (340)
41: 161 169 176 (355)
42: 235 229 234 (4150)  #
43: 234 229 233 (4138)  #
44: 233 228 233 (4119)  #
45: 225 220 225 (3602)  #
46: 151 158 164 (329)
47: 145 152 159 (362)
48: 146 153 160 (377)
49: 232 228 232 (4113)  #
50: 232 228 232 (4113)  #
51: 232 227 232 (4065)  #
52: 231 226 231 (4055)  #
53: 138 146 153 (355)
54: 137 146 153 (333)
55: 139 148 155 (316)
56: 138 147 154 (322)
# ...
```

#### Step 3: Let's give it another shot with `threshold = 200`
```bash
# after adjusting our threshold, we successfully decode the clip
$> python clip2morse.py --clip ./clips/sample_1_SOS_SOS.mov -t 200
Frame data saved to output/raw_net_color.txt

Morse Code:
/ ... --- ... / ... --- ...

Decoded Text:
SOS SOS
```

## General Algorithm

#### 1. Load and preprocess video:
Read each frame from the input video and resize it for consistent analysis.

#### 2. Compare each frame to the baseline:
Use the first frame as a reference and calculate pixel-wise differences to detect visible changes (i.e., flashing light).

#### 3. Filter and average changed pixels:
Exclude unchanged pixels using a brightness tolerance, then compute the average RGB of only the changed pixels.

#### 4. Classify each frame as ON or OFF:
Convert the average RGB to a brightness score and mark frames as "ON" if the score exceeds a defined threshold.

#### 5. Group consecutive frames:
Group sequences of ON and OFF frames and measure their durations to extract signal pulses and gaps.

#### 6. Cluster ON durations:
Use KMeans to dynamically separate ON durations into short (dot) and long (dash) clusters.

#### 7. Cluster OFF durations:
Apply KMeans to OFF durations to separate them into intra-symbol, letter, and word gap categories.

#### 8. Map clusters to signal roles:
Sort cluster centers and assign labels based on duration (shortest = intra-symbol, etc.).

#### 9. Construct Morse symbols:
Build Morse code strings from the ordered ON/OFF groups using the classified dot/dash and spacing roles.

#### 10. Decode Morse to text:
Translate the Morse code into readable text using a standard Morse code dictionary.


## Design Challenges
_Room for improvement to handle more variations_

### True Morse vs. Common Morse

Take the classic **SOS** signal. In the official format, it's:

```
... --- ... / ... --- ...
```

But in real-world videos like [this example](https://www.youtube.com/watch?v=k8m8R4x0Mgk), it's often transmitted more like:

```
...---......---...
```

Here, the **gaps between symbols, letters, and even words** are inconsistent or missing entirely. Without clear separation, someone unfamiliar with Morse wouldn’t be able to decode the message reliably because it violates standard timing rules.

---

### Timing Variation Across Clips

Different operators and devices introduce significant **variation in timing**:
- Dashes and dots may vary in duration between videos.
- Gaps between elements may be subtle or missing.
- Frame rates and lighting inconsistencies add noise.

Expecting users to manually adjust timing thresholds for each clip is impractical.

---

### The Current Answer: KMeans Clustering

To solve this, we use **KMeans clustering** to automatically adapt to each clip’s unique timing patterns:

- **ON durations** are clustered into `dot` vs `dash`.
- **OFF durations** are clustered into `intra-symbol`, `letter`, and `word` gaps.

This makes decoding **robust and automatic**, even when the source signal is noisy or non-standard. It removes the need for calibration, letting the script intelligently interpret Morse from real-world video signals.

## Resource Links

[FlashLight SOS Example Video](https://www.youtube.com/watch?v=k8m8R4x0Mgk)

[CyberChef Morse Calculator](https://gchq.github.io/CyberChef/#recipe=To_Morse_Code('-/.','Space','Forward%20slash')From_Morse_Code('Space','Forward%20slash'/disabled)&input=U09TIFNPUw&ieol=CRLF)

[Beginner K-Means Clustering w/ Python](https://medium.com/@amit25173/k-means-clustering-for-dummies-a-beginners-guide-399fb8c427fd)

[Morse Flashlight iOS App](https://apps.apple.com/us/app/flashlight-morse-utility/id386426585)