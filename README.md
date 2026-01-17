# 🎙️ Voice-Guided Intelligent Vision Assistant

## 📌 Project Overview

The Voice-Guided Intelligent Vision Assistant is an AI-powered assistive application designed to support visually impaired users through real-time face analysis and voice-based interaction.
The system identifies people as known or unknown, estimates their distance and position, and provides spoken descriptions based on facial analysis results.

The entire application is controlled using voice commands, enabling hands-free and accessible usage.

## 🎯 Key Objectives

- Assist visually impaired users using AI and voice guidance
- Identify people as known or unknown
- Provide facial attributes and identity-related information via speech
- Enable full interaction through voice commands

## ✨ Core Features

### 👤 Person Identification

- Real-time person detection using camera input
- Classifies individuals into:
   **Known Person / Unknown Person**
  
- 🧠 Known Person Recognition

For known individuals, the system provides:
**Person name / Last seen information / Approximate distance / Relative position (left, right, center)**


- 🧑 Unknown Person Analysis

For unknown individuals, the system identifies:
**Estimated age / Gender / Facial attributes (glasses, beard, smile, etc.) / Approximate distance / Position**


- 📏 Distance & Position Estimation

Estimates distance between the user and detected person
Determines relative position:
**Left / Right / Center**

- 🎙️ Voice Command Support

The application is fully controlled using voice commands such as:

- 🔊 Text-to-Speech Feedback

Converts detection and analysis results into clear voice output

Reduces dependency on visual interfaces


## 🏗️ System Architecture

- Camera captures real-time video frames
- Face detection and feature extraction
- Classification as known or unknown
- Facial attribute and identity analysis
- Distance and position estimation
- Text-to-speech conversion
- Voice-based user interaction

## 📂 Datasets Used

### Unknown Person Facial Attribute Dataset

- Used to train and evaluate age, gender, and facial attribute prediction models.
- Publicly available datasets include:
  ### UTKFace Dataset

- Used for age and gender estimation
- Contains diverse face images with age and gender labels

  ### CelebA Dataset

- Used for facial attribute recognition
- Includes attributes such as glasses, beard, smile, and hair type

**Trained Models** [models](models)

## 🧪 Technologies Used

- Computer Vision – Face detection and tracking
- Machine Learning / AI – Face recognition and attribute prediction
- Speech Recognition – Voice command processing
- Text-to-Speech (TTS) – Audio feedback
- OpenCV
- Python / JavaScript (implementation dependent)

### 📊 Evaluation Metrics

- Age and gender prediction accuracy
- Facial attribute classification accuracy
