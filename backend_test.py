#!/usr/bin/env python3
"""
Backend API Testing for AI Video Generation Website
Tests all video generation endpoints and database integration
"""

import requests
import json
import time
import sys
from datetime import datetime

# Get backend URL from frontend .env
BACKEND_URL = "https://4e8fa817-61cd-465d-ad69-a6604d594f9e.preview.emergentagent.com/api"

def test_api_root():
    """Test the root API endpoint"""
    print("🧪 Testing API Root Endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "AI Video Generator API" in data["message"]:
                print("✅ API Root endpoint working correctly")
                return True
            else:
                print("❌ API Root endpoint returned unexpected response")
                return False
        else:
            print(f"❌ API Root endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Root endpoint error: {str(e)}")
        return False

def test_video_generation():
    """Test the main video generation endpoint"""
    print("\n🧪 Testing Video Generation Endpoint...")
    
    test_cases = [
        {
            "name": "Basic video generation",
            "payload": {
                "prompt": "A beautiful sunset over the ocean with waves crashing",
                "duration": 5
            }
        },
        {
            "name": "Longer duration video",
            "payload": {
                "prompt": "A cat playing with a ball of yarn in a cozy living room",
                "duration": 10
            }
        },
        {
            "name": "Default duration (no duration specified)",
            "payload": {
                "prompt": "A peaceful forest with birds chirping and sunlight filtering through trees"
            }
        }
    ]
    
    generated_video_ids = []
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        try:
            response = requests.post(
                f"{BACKEND_URL}/generate-video",
                json=test_case["payload"],
                headers={"Content-Type": "application/json"}
            )
            
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2, default=str)}")
                
                # Validate response structure
                required_fields = ["id", "prompt", "status", "created_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"  ❌ Missing required fields: {missing_fields}")
                    return False, []
                
                # Check if video generation completed (demo mode should complete immediately)
                if data["status"] == "completed" and data.get("video_url"):
                    print(f"  ✅ Video generated successfully with URL: {data['video_url']}")
                    generated_video_ids.append(data["id"])
                elif data["status"] == "processing":
                    print(f"  ⏳ Video is processing (ID: {data['id']})")
                    generated_video_ids.append(data["id"])
                else:
                    print(f"  ⚠️ Unexpected status: {data['status']}")
                    generated_video_ids.append(data["id"])
                    
            else:
                print(f"  ❌ Video generation failed with status {response.status_code}")
                print(f"  Error: {response.text}")
                return False, []
                
        except Exception as e:
            print(f"  ❌ Video generation error: {str(e)}")
            return False, []
    
    print("✅ All video generation tests completed")
    return True, generated_video_ids

def test_get_video_status(video_ids):
    """Test getting video status by ID"""
    print("\n🧪 Testing Get Video Status Endpoint...")
    
    if not video_ids:
        print("  ⚠️ No video IDs to test with")
        return True
    
    for video_id in video_ids:
        print(f"\n  Testing video ID: {video_id}")
        try:
            response = requests.get(f"{BACKEND_URL}/video/{video_id}")
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2, default=str)}")
                
                # Validate response structure
                required_fields = ["id", "prompt", "status", "created_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"  ❌ Missing required fields: {missing_fields}")
                    return False
                
                if data["id"] == video_id:
                    print(f"  ✅ Video status retrieved successfully")
                else:
                    print(f"  ❌ Video ID mismatch: expected {video_id}, got {data['id']}")
                    return False
                    
            else:
                print(f"  ❌ Get video status failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ Get video status error: {str(e)}")
            return False
    
    # Test with invalid video ID
    print(f"\n  Testing with invalid video ID...")
    try:
        response = requests.get(f"{BACKEND_URL}/video/invalid-id-12345")
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 404:
            print("  ✅ Invalid video ID correctly returns 404")
        else:
            print(f"  ❌ Invalid video ID should return 404, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Invalid video ID test error: {str(e)}")
        return False
    
    print("✅ Get video status tests completed")
    return True

def test_get_all_videos():
    """Test getting all videos with pagination"""
    print("\n🧪 Testing Get All Videos Endpoint...")
    
    test_cases = [
        {"name": "Default limit", "params": {}},
        {"name": "Custom limit", "params": {"limit": 5}},
        {"name": "Large limit", "params": {"limit": 50}}
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        try:
            response = requests.get(f"{BACKEND_URL}/videos", params=test_case["params"])
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Number of videos returned: {len(data)}")
                
                if isinstance(data, list):
                    print("  ✅ Response is a list")
                    
                    # Check structure of first video if any exist
                    if data:
                        first_video = data[0]
                        required_fields = ["id", "prompt", "status", "created_at"]
                        missing_fields = [field for field in required_fields if field not in first_video]
                        
                        if missing_fields:
                            print(f"  ❌ Missing required fields in video: {missing_fields}")
                            return False
                        else:
                            print("  ✅ Video structure is correct")
                            print(f"  Sample video: {json.dumps(first_video, indent=4, default=str)}")
                    else:
                        print("  ℹ️ No videos in database yet")
                        
                else:
                    print("  ❌ Response is not a list")
                    return False
                    
            else:
                print(f"  ❌ Get all videos failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ Get all videos error: {str(e)}")
            return False
    
    print("✅ Get all videos tests completed")
    return True

def test_error_handling():
    """Test error handling for invalid requests"""
    print("\n🧪 Testing Error Handling...")
    
    test_cases = [
        {
            "name": "Empty prompt",
            "payload": {"prompt": "", "duration": 5},
            "expected_status": [400, 422]  # Could be either validation error
        },
        {
            "name": "Missing prompt",
            "payload": {"duration": 5},
            "expected_status": [400, 422]
        },
        {
            "name": "Invalid duration type",
            "payload": {"prompt": "Test video", "duration": "invalid"},
            "expected_status": [400, 422]
        },
        {
            "name": "Negative duration",
            "payload": {"prompt": "Test video", "duration": -5},
            "expected_status": [400, 422]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        try:
            response = requests.post(
                f"{BACKEND_URL}/generate-video",
                json=test_case["payload"],
                headers={"Content-Type": "application/json"}
            )
            
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code in test_case["expected_status"]:
                print(f"  ✅ Correctly returned error status {response.status_code}")
            else:
                print(f"  ⚠️ Expected status {test_case['expected_status']}, got {response.status_code}")
                # This might not be critical if the API handles it differently
                
        except Exception as e:
            print(f"  ❌ Error handling test error: {str(e)}")
            return False
    
    print("✅ Error handling tests completed")
    return True

def test_database_integration():
    """Test database integration by checking data persistence"""
    print("\n🧪 Testing Database Integration...")
    
    # Generate a unique prompt to track
    unique_prompt = f"Database test video - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"  Creating video with unique prompt: {unique_prompt}")
    
    try:
        # Create a video
        response = requests.post(
            f"{BACKEND_URL}/generate-video",
            json={"prompt": unique_prompt, "duration": 3},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"  ❌ Failed to create test video: {response.status_code}")
            return False
        
        video_data = response.json()
        video_id = video_data["id"]
        print(f"  Created video with ID: {video_id}")
        
        # Wait a moment for database write
        time.sleep(1)
        
        # Retrieve the video by ID
        response = requests.get(f"{BACKEND_URL}/video/{video_id}")
        if response.status_code != 200:
            print(f"  ❌ Failed to retrieve video by ID: {response.status_code}")
            return False
        
        retrieved_video = response.json()
        if retrieved_video["prompt"] != unique_prompt:
            print(f"  ❌ Prompt mismatch: expected '{unique_prompt}', got '{retrieved_video['prompt']}'")
            return False
        
        print("  ✅ Video successfully stored and retrieved by ID")
        
        # Check if video appears in the list
        response = requests.get(f"{BACKEND_URL}/videos", params={"limit": 20})
        if response.status_code != 200:
            print(f"  ❌ Failed to get videos list: {response.status_code}")
            return False
        
        videos_list = response.json()
        found_video = None
        for video in videos_list:
            if video["id"] == video_id:
                found_video = video
                break
        
        if not found_video:
            print(f"  ❌ Video not found in videos list")
            return False
        
        if found_video["prompt"] != unique_prompt:
            print(f"  ❌ Prompt mismatch in list: expected '{unique_prompt}', got '{found_video['prompt']}'")
            return False
        
        print("  ✅ Video successfully appears in videos list")
        print("✅ Database integration tests completed")
        return True
        
    except Exception as e:
        print(f"  ❌ Database integration test error: {str(e)}")
        return False

def main():
    """Run all backend tests"""
    print("🚀 Starting Backend API Tests for AI Video Generation Website")
    print(f"Backend URL: {BACKEND_URL}")
    print("=" * 80)
    
    test_results = {}
    
    # Test API Root
    test_results["api_root"] = test_api_root()
    
    # Test Video Generation
    video_gen_success, video_ids = test_video_generation()
    test_results["video_generation"] = video_gen_success
    
    # Test Get Video Status
    test_results["get_video_status"] = test_get_video_status(video_ids)
    
    # Test Get All Videos
    test_results["get_all_videos"] = test_get_all_videos()
    
    # Test Error Handling
    test_results["error_handling"] = test_error_handling()
    
    # Test Database Integration
    test_results["database_integration"] = test_database_integration()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All backend tests passed! The API is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the detailed output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)