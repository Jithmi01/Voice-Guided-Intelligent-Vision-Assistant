#final code


import os
import cv2
import numpy as np
import pickle
from pathlib import Path
import time
import queue
from threading import Thread

# TTS Setup
try:
    import win32com.client
    USE_WINDOWS_TTS = True
except ImportError:
    USE_WINDOWS_TTS = False

try:
    import pyttsx3
    USE_PYTTSX3 = True
except ImportError:
    USE_PYTTSX3 = False

# Speech Recognition Setup
try:
    import speech_recognition as sr
    USE_SPEECH_RECOGNITION = True
except ImportError:
    USE_SPEECH_RECOGNITION = False

# Face Recognition Setup
try:
    from deepface import DeepFace
    USE_DEEPFACE = True
    print("✅ Using DeepFace (High Accuracy)")
except ImportError:
    USE_DEEPFACE = False
    print("⚠️ DeepFace not available. Install: pip install deepface tf-keras")

class FaceRecognitionSystem:
    def __init__(self, known_faces_dir="data/known_faces", embeddings_dir="data/embeddings"):
        self.known_faces_dir = known_faces_dir
        self.embeddings_dir = embeddings_dir
        self.known_embeddings = {}
        self.threshold = 0.75
        self.model_name = "Facenet512"
        
        # Voice settings
        self.last_announcement = {}
        self.announcement_cooldown = 3
        self.voice_enabled = True
        
        # NEW: Detection cooldown settings (2 minutes = 120 seconds)
        self.detection_cooldown = 20  # 2 minutes in seconds
        self.last_detection = {}  # Store last detection time for each person
        self.detection_display_duration = 5  # Show detection for 5 seconds after initial detection

        # NEW: Last seen time tracking
        self.last_seen_time = {}  # Store last seen datetime for each known person
        self.last_seen_file = os.path.join(self.embeddings_dir, "last_seen.pkl")
        self.load_last_seen()  # Load last seen info at startup

        # Initialize Face Recognition
        if USE_DEEPFACE:
            print(f" DeepFace ready with {self.model_name} model")
        else:
            print(" No face recognition model available")
        
        # Speech Recognition
        if USE_SPEECH_RECOGNITION:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            print("🎤 Calibrating microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print(" Microphone ready")
        else:
            self.recognizer = None
            self.microphone = None
        
        # TTS Worker
        self.speech_queue = queue.Queue()
        self.speech_thread = Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()
        
        # Create directories
        Path(self.known_faces_dir).mkdir(parents=True, exist_ok=True)
        Path(self.embeddings_dir).mkdir(parents=True, exist_ok=True)
        
        # Load embeddings
        self.load_embeddings()

    def _speech_worker(self):
        """TTS worker thread"""
        try:
            if USE_WINDOWS_TTS:
                import pythoncom
                pythoncom.CoInitialize()
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Rate = 1
                speaker.Volume = 100
                print(" Windows TTS initialized")
                
                while True:
                    text = self.speech_queue.get()
                    if text is None:
                        break
                    print(f" Speaking: {text}")
                    speaker.Speak(text)
                pythoncom.CoUninitialize()
                
            elif USE_PYTTSX3:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.setProperty('volume', 1.0)
                print(" pyttsx3 TTS initialized")
                
                while True:
                    text = self.speech_queue.get()
                    if text is None:
                        break
                    print(f"🔊 Speaking: {text}")
                    engine.say(text)
                    engine.runAndWait()
        except Exception as e:
            print(f" TTS Error: {str(e)}")

    def speak(self, text):
        if self.voice_enabled:
            self.speech_queue.put(text)

    def listen_for_command(self, prompt=""):
        if not USE_SPEECH_RECOGNITION:
            return None
        
        try:
            if prompt:
                print(f"🎤 {prompt}")
                self.speak(prompt)
            
            with self.microphone as source:
                print("🎤 Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            print(" Recognizing...")
            text = self.recognizer.recognize_google(audio)
            print(f" You said: {text}")
            return text.lower()
        except Exception as e:
            print(f"❌ Speech error: {str(e)}")
            return None

    def parse_voice_command(self, command):
        if not command:
            return None
        
        command_map = {
            "generate": 1, "register": 1, "one": 1,
            "start": 2, "webcam": 2, "camera": 2, "two": 2,
            "test": 3, "image": 3, "three": 3,
            "show": 4, "list": 4, "four": 4,
            "threshold": 5, "five": 5,
            "toggle": 6, "voice": 6, "six": 6,
            "test voice": 7, "seven": 7,
            "exit": 8, "quit": 8, "eight": 8
        }
        
        for keyword, option in command_map.items():
            if keyword in command:
                return option
        
        for char in command:
            if char.isdigit():
                num = int(char)
                if 1 <= num <= 8:
                    return num
        return None

    def extract_face_embedding(self, image):
        """Extract face embedding using DeepFace"""
        if not USE_DEEPFACE:
            return None
        
        try:
            embeddings = DeepFace.represent(
                img_path=image,
                model_name=self.model_name,
                enforce_detection=False,
                detector_backend='opencv'
            )
            
            if embeddings and len(embeddings) > 0:
                return np.array(embeddings[0]["embedding"])
            return None
        except Exception as e:
            return None

    def generate_embeddings(self):
        """Generate embeddings for all known faces"""
        print("🔄 Generating embeddings...")
        self.known_embeddings = {}
        
        if not os.path.exists(self.known_faces_dir):
            print(f"❌ Directory not found!")
            return
        
        for person_name in os.listdir(self.known_faces_dir):
            person_path = os.path.join(self.known_faces_dir, person_name)
            if not os.path.isdir(person_path):
                continue
            
            print(f"📸 Processing {person_name}...")
            embeddings_list = []
            
            for img_file in os.listdir(person_path):
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(person_path, img_file)
                    try:
                        image = cv2.imread(img_path)
                        if image is None:
                            print(f"  ⚠️ Could not load {img_file}")
                            continue
                        
                        embedding = self.extract_face_embedding(image)
                        if embedding is not None:
                            embedding = embedding / np.linalg.norm(embedding)
                            embeddings_list.append(embedding)
                            print(f"  ✅ {img_file} (embedding shape: {embedding.shape})")
                        else:
                            print(f"  ⚠️ No face in {img_file}")
                    except Exception as e:
                        print(f"  ❌ Failed: {str(e)}")
            
            if embeddings_list:
                self.known_embeddings[person_name] = {
                    "embeddings": embeddings_list,
                    "count": len(embeddings_list)
                }
                print(f"✅ {person_name}: {len(embeddings_list)} embeddings")
        
        # Verify uniqueness
        print("\n🔍 Verifying uniqueness...")
        names = list(self.known_embeddings.keys())
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                distances = []
                for emb1 in self.known_embeddings[names[i]]["embeddings"]:
                    for emb2 in self.known_embeddings[names[j]]["embeddings"]:
                        dist = np.linalg.norm(emb1 - emb2)
                        distances.append(dist)
                
                avg_dist = np.mean(distances)
                min_dist = np.min(distances)
                print(f"  {names[i]} vs {names[j]}: avg={avg_dist:.3f}, min={min_dist:.3f}")
                
                if min_dist < 0.4:
                    print(f"    ⚠️ WARNING: Very similar!")
                elif min_dist > 0.6:
                    print(f"    ✅ Good separation")
        
        self.save_embeddings()
        print(f"\n🎉 Registered: {len(self.known_embeddings)} people")
        print(f"💡 Recommended threshold: 0.70-0.80 (current: {self.threshold})")

    def save_embeddings(self):
        embeddings_file = os.path.join(self.embeddings_dir, "deepface_embeddings.pkl")
        with open(embeddings_file, 'wb') as f:
            pickle.dump(self.known_embeddings, f)
        print(f"💾 Saved to {embeddings_file}")

    def load_embeddings(self):
        embeddings_file = os.path.join(self.embeddings_dir, "deepface_embeddings.pkl")
        if os.path.exists(embeddings_file):
            with open(embeddings_file, 'rb') as f:
                self.known_embeddings = pickle.load(f)
            print(f"✅ Loaded {len(self.known_embeddings)} people")
        else:
            print("⚠️ No embeddings found. Run option 1 first.")

    def save_last_seen(self):
        try:
            with open(self.last_seen_file, 'wb') as f:
                pickle.dump(self.last_seen_time, f)
            print("💾 Last seen times saved")
        except Exception as e:
            print(f"❌ Failed to save last seen: {e}")

    def load_last_seen(self):
        if os.path.exists(self.last_seen_file):
            try:
                with open(self.last_seen_file, 'rb') as f:
                    self.last_seen_time = pickle.load(f)
                print("✅ Loaded last seen times")
            except Exception as e:
                print(f"❌ Failed to load last seen: {e}")

    def recognize_face(self, embedding):
        """Recognize face with improved adaptive thresholding"""
        if embedding is None or not self.known_embeddings:
            return "Unknown", 1.0
        
        best_match = "Unknown"
        min_distance = float('inf')
        all_distances = {}
        
        embedding = embedding / np.linalg.norm(embedding)
        
        for name, data in self.known_embeddings.items():
            distances = []
            for stored_emb in data["embeddings"]:
                stored_emb_norm = stored_emb / np.linalg.norm(stored_emb)
                dist = np.linalg.norm(embedding - stored_emb_norm)
                distances.append(dist)
            
            min_dist = np.min(distances)
            all_distances[name] = min_dist
            
            if min_dist < min_distance:
                min_distance = min_dist
                best_match = name
        
        dist_str = ', '.join([f'{n}:{d:.3f}' for n, d in sorted(all_distances.items(), key=lambda x: x[1])])
        print(f"🔍 Distances: {dist_str}")
        print(f"   Threshold: {self.threshold}, Min Distance: {min_distance:.3f}")
        
        sorted_dists = sorted(all_distances.items(), key=lambda x: x[1])
        if len(sorted_dists) >= 2:
            best_name, best_dist = sorted_dists[0]
            second_name, second_dist = sorted_dists[1]
            margin = second_dist - best_dist
            margin_ratio = margin / best_dist if best_dist > 0 else 0
            
            print(f"   Best: {best_name}={best_dist:.3f}, 2nd: {second_name}={second_dist:.3f}")
            print(f"   Margin: {margin:.3f} ({margin_ratio:.1%})")
            
            if best_dist <= self.threshold or margin_ratio > 0.30:
                print(f"✅ Matched: {best_match}")
                return best_match, min_distance
            else:
                print(f"❌ No confident match")
                return "Unknown", min_distance
        else:
            if min_distance <= self.threshold * 1.2:
                print(f"✅ Matched: {best_match}")
                return best_match, min_distance
            else:
                print(f"❌ No match")
                return "Unknown", min_distance

    def should_announce(self, name):
        current_time = time.time()
        if name not in self.last_announcement:
            self.last_announcement[name] = current_time
            return True
        
        if current_time - self.last_announcement[name] >= self.announcement_cooldown:
            self.last_announcement[name] = current_time
            return True
        
        return False

    def can_detect_person(self, name):
        """NEW: Check if person can be detected (2-minute cooldown)"""
        current_time = time.time()
        
        # If person hasn't been detected before, allow detection
        if name not in self.last_detection:
            return True
        
        # Check if cooldown period has passed
        time_since_last = current_time - self.last_detection[name]
        if time_since_last >= self.detection_cooldown:
            return True
        
        return False

    def record_detection(self, name):
        """Record that a person was detected"""
        self.last_detection[name] = time.time()
        self.last_seen_time[name] = time.strftime("%Y/%m/%d %I:%M %p", time.localtime())
        self.save_last_seen()
        print(f"⏱️  {name} detected. Next detection available in {self.detection_cooldown} seconds")

    def get_time_until_next_detection(self, name):
        """NEW: Get remaining cooldown time for a person"""
        if name not in self.last_detection:
            return 0
        
        current_time = time.time()
        elapsed = current_time - self.last_detection[name]
        remaining = max(0, self.detection_cooldown - elapsed)
        return int(remaining)

    def calculate_direction_and_distance(self, face_rect, frame_width, focal_length=700, real_face_width=0.15):
        """Calculate direction and approximate distance in meters"""
        x, y, w, h = face_rect['x'], face_rect['y'], face_rect['w'], face_rect['h']
        face_center_x = x + w / 2
        frame_center_x = frame_width / 2
        
        if face_center_x < frame_center_x * 0.8:
            direction = "left"
        elif face_center_x > frame_center_x * 1.2:
            direction = "right"
        else:
            direction = "center"
        
        distance = (focal_length * real_face_width) / w
        return direction, round(distance, 2)

    def announce_person(self, name, distance, direction=None):
        if not self.voice_enabled or not self.should_announce(name):
            return
        
        confidence = max(0, 100 - int(distance * 100))
        
        if name == "Unknown":
            message = "Unknown person detected"
        else:
            # Build last seen message
            last_seen_msg = ""
            if name in self.last_seen_time:
                last_seen_str = self.last_seen_time[name]
                message_time = time.strptime(last_seen_str, "%Y/%m/%d %I:%M %p")
                today = time.localtime()
                if message_time.tm_year == today.tm_year and message_time.tm_yday == today.tm_yday:
                    last_seen_msg = f", you met {name} today at {time.strftime('%I:%M %p', message_time)}"
                else:
                    last_seen_msg = f", you met {name} on {last_seen_str}"
            
            if confidence >= 85:
                message = f"Hello {name}"
            elif confidence >= 70:
                message = f"I think this is {name}"
            else:
                message = f"Possibly {name}"
            
            message += last_seen_msg
        
        # Always add direction and distance
        if direction:
            message += f" on your {direction}, approximately {distance} meters away"
        
        print(f"📢 {message}")
        self.speech_queue.put(message)

    def recognize_from_webcam(self):
        """Real-time face recognition from webcam with 2-minute cooldown"""
        if not self.known_embeddings:
            print("❌ No embeddings! Run option 1 first")
            self.speak("No face database found")
            return
        
        if not USE_DEEPFACE:
            print("❌ DeepFace not available")
            self.speak("Face recognition not available")
            return
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        print("🎥 Starting... Press 'q'=quit, 'v'=toggle voice")
        self.speak("Face recognition started")
        
        frame_count = 0
        last_process = time.time()
        recognition_cache = {}
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_width = frame.shape[1]
            current_time = time.time()
            
            # Process every 20 frames or 1 second
            if frame_count % 20 == 0 or (current_time - last_process) > 1.0:
                try:
                    # First, detect if there's a face in the frame
                    faces = DeepFace.extract_faces(
                        img_path=frame,
                        detector_backend='opencv',
                        enforce_detection=False
                    )
                    
                    # Only proceed if a face is actually detected
                    if faces and len(faces) > 0:
                        face_rect = faces[0]['facial_area']
                        direction, distance_in_meters = self.calculate_direction_and_distance(face_rect, frame_width)
                        
                        # Now extract embedding for recognition
                        embedding = self.extract_face_embedding(frame)
                        
                        if embedding is not None:
                            name, distance = self.recognize_face(embedding)
                            
                            # Check if this person can be detected (cooldown check)
                            if self.can_detect_person(name):
                                # Announce with position and distance (works for both known and unknown)
                                self.announce_person(name, distance_in_meters, direction)
                                self.record_detection(name)
                                
                                x, y, w, h = face_rect['x'], face_rect['y'], face_rect['w'], face_rect['h']
                                recognition_cache = {
                                    'name': name,
                                    'distance': distance_in_meters,
                                    'bbox': (x, y, x+w, y+h),
                                    'direction': direction,
                                    'timestamp': current_time
                                }
                            else:
                                # Person is in cooldown - show time remaining
                                remaining = self.get_time_until_next_detection(name)
                                print(f"⏳ {name} in cooldown. Next detection in {remaining} seconds")
                                
                                # Clear cache if display duration expired
                                if recognition_cache and 'timestamp' in recognition_cache:
                                    if current_time - recognition_cache['timestamp'] > self.detection_display_duration:
                                        recognition_cache.clear()
                        else:
                            # Face detected but couldn't extract embedding
                            print("⚠️ Face detected but could not extract features")
                            if recognition_cache and 'timestamp' in recognition_cache:
                                if current_time - recognition_cache['timestamp'] > self.detection_display_duration:
                                    recognition_cache.clear()
                    else:
                        # No face detected - clear cache if display duration expired
                        if recognition_cache and 'timestamp' in recognition_cache:
                            if current_time - recognition_cache['timestamp'] > self.detection_display_duration:
                                recognition_cache.clear()
                    
                    last_process = current_time
                
                except Exception as e:
                    print(f"❌ Error: {str(e)}")
            
            # Draw results (only if within display duration)
            if recognition_cache:
                if 'timestamp' not in recognition_cache or (current_time - recognition_cache['timestamp']) <= self.detection_display_duration:
                    name = recognition_cache['name']
                    distance = recognition_cache['distance']
                    bbox = recognition_cache['bbox']
                    direction = recognition_cache['direction']
                    
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    confidence = max(0, 100 - int(distance * 100))
                    
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 3)
                    label = f"{name} ({confidence}%) - {direction}, {distance}m"
                    
                    cv2.rectangle(frame, (bbox[0], bbox[1]-40), (bbox[2], bbox[1]), color, -1)
                    cv2.putText(frame, label, (bbox[0]+5, bbox[1]-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                else:
                    recognition_cache.clear()
            
            voice_status = "🔊" if self.voice_enabled else "🔇"
            cv2.putText(frame, f"{voice_status} Press 'q'=quit 'v'=toggle", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('VoiceVision Face Recognition', frame)
            frame_count += 1
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.speak("Goodbye")
                time.sleep(0.5)
                break
            elif key == ord('v'):
                self.voice_enabled = not self.voice_enabled
                status = "enabled" if self.voice_enabled else "disabled"
                print(f"🔊 Voice {status}")
                self.speak(f"Voice {status}")
        
        cap.release()
        cv2.destroyAllWindows()

    def test_recognition(self, img_path):
        """Test recognition on single image"""
        if not os.path.exists(img_path):
            print("❌ Image not found")
            self.speak("Image not found")
            return
        
        print(f"🔍 Testing: {img_path}")
        self.speak("Testing recognition")
        
        img = cv2.imread(img_path)
        if img is None:
            print("❌ Could not load image")
            self.speak("Could not load image")
            return
        
        try:
            faces = DeepFace.extract_faces(
                img_path=img_path,
                detector_backend='opencv',
                enforce_detection=False
            )
            
            if not faces:
                print("⚠️ No faces detected")
                self.speak("No faces detected")
                return
            
            print(f"✅ Found {len(faces)} face(s)")
            self.speak(f"Found {len(faces)} faces")
            
            for i, face_data in enumerate(faces):
                embedding = self.extract_face_embedding(img)
                if embedding is not None:
                    name, distance = self.recognize_face(embedding)
                    print(f"  Face {i+1}: {name} (distance: {distance:.3f})")
                    
                    if i == 0:
                        self.announce_person(name, distance)
                    
                    face_rect = face_data['facial_area']
                    x, y, w, h = face_rect['x'], face_rect['y'], face_rect['w'], face_rect['h']
                    
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    confidence = max(0, 100 - int(distance * 100))
                    
                    cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
                    label = f"{name} ({confidence}%)"
                    
                    cv2.rectangle(img, (x, y-30), (x+w, y), color, -1)
                    cv2.putText(img, label, (x+5, y-8),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow('Recognition Result', img)
            print("Press any key to close...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.speak("Error processing image")

# Main Menu
if __name__ == "__main__":
    face_system = FaceRecognitionSystem()
    face_system.speak("Welcome to Voice Vision")
    
    while True:
        print("\n" + "="*60)
        print("🧠 VOICEVISION - FACE RECOGNITION SYSTEM")
        print("="*60)
        print("1. Generate embeddings from known faces")
        print("2. Start webcam recognition")
        print("3. Test on single image")
        print("4. Show registered people")
        print("5. Change threshold (current: {:.2f})".format(face_system.threshold))
        print("6. Toggle voice (current: {})".format("ON" if face_system.voice_enabled else "OFF"))
        print("7. Test voice output")
        print("8. Exit")
        print("="*60)
        print(f"⏱️  Detection Cooldown: {face_system.detection_cooldown} seconds (2 minutes)")
        print("="*60)
        
        if USE_SPEECH_RECOGNITION:
            print("💡 Press Enter for voice command, or type number (1-8)")
            choice_input = input("Choose: ").strip().lower()
        else:
            choice_input = input("Choose (1-8): ").strip()
        
        if USE_SPEECH_RECOGNITION and (choice_input == "" or choice_input == "voice"):
            command = face_system.listen_for_command("Say your command")
            choice = face_system.parse_voice_command(command) if command else None
            if choice:
                face_system.speak(f"Option {choice}")
            else:
                face_system.speak("Not recognized")
                continue
        else:
            try:
                choice = int(choice_input)
            except:
                print("❌ Invalid")
                continue
        
        if choice == 1:
            face_system.speak("Starting registration")
            face_system.generate_embeddings()
            face_system.speak("Registration complete")
        
        elif choice == 2:
            face_system.recognize_from_webcam()
        
        elif choice == 3:
            img_path = input("Image path: ").strip()
            if img_path:
                face_system.test_recognition(img_path)
        
        elif choice == 4:
            print("\n📋 Registered People:")
            if face_system.known_embeddings:
                for name, data in face_system.known_embeddings.items():
                    print(f"  • {name} ({data['count']} images)")
                names = ', '.join(face_system.known_embeddings.keys())
                face_system.speak(f"Registered: {names}")
            else:
                print("  None")
                face_system.speak("No one registered")
        
        elif choice == 5:
            try:
                new_threshold = float(input("New threshold (0.3-0.8, lower=stricter): "))
                if 0.2 <= new_threshold <= 1.0:
                    face_system.threshold = new_threshold
                    print(f"✅ Set to {new_threshold:.2f}")
                    face_system.speak(f"Threshold {new_threshold:.2f}")
                else:
                    print("❌ Invalid range")
            except:
                print("❌ Invalid")
        
        elif choice == 6:
            face_system.voice_enabled = not face_system.voice_enabled
            status = "enabled" if face_system.voice_enabled else "disabled"
            print(f"🔊 Voice {status}")
            face_system.speak(f"Voice {status}")
        
        elif choice == 7:
            face_system.speak("Testing voice output. This is working correctly.")
        
        elif choice == 8:
            print("👋 Goodbye!")
            face_system.speak("Goodbye")
            break
        
        else:
            print("❌ Invalid")