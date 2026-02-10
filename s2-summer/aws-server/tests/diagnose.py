#!/usr/bin/env python3
"""
AWS IoT Connection Troubleshooting Script
Run this to diagnose connection issues
"""

import os
import json
import subprocess
import socket
from pathlib import Path

# Your configuration
IOT_ENDPOINT = "a1ajomln5m8rkh-ats.iot.ap-southeast-2.amazonaws.com"
PATH_TO_CERT = "certs/device.pem.crt"
PATH_TO_KEY = "certs/private.pem.key"
PATH_TO_ROOT = "certs/AmazonRootCA1.pem"

def check_files():
    """Check if certificate files exist and are readable."""
    print("🔍 Checking certificate files...")
    
    files = {
        "Device Certificate": PATH_TO_CERT,
        "Private Key": PATH_TO_KEY,
        "Root CA": PATH_TO_ROOT
    }
    
    all_good = True
    for name, path in files.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            perms = oct(os.stat(path).st_mode)[-3:]
            print(f"  ✅ {name}: {path} ({size} bytes, perms: {perms})")
            
            # Check if file is readable
            try:
                with open(path, 'r') as f:
                    content = f.read(100)  # Read first 100 chars
                    if 'BEGIN CERTIFICATE' in content or 'BEGIN RSA PRIVATE KEY' in content or 'BEGIN PRIVATE KEY' in content:
                        print(f"    📄 File format looks correct")
                    else:
                        print(f"    ⚠️  File format might be incorrect")
            except Exception as e:
                print(f"    ❌ Cannot read file: {e}")
                all_good = False
        else:
            print(f"  ❌ {name}: {path} - FILE NOT FOUND")
            all_good = False
    
    return all_good

def check_network():
    """Check network connectivity to IoT endpoint."""
    print(f"\n🌐 Checking network connectivity to {IOT_ENDPOINT}...")
    
    try:
        # DNS resolution
        ip = socket.gethostbyname(IOT_ENDPOINT)
        print(f"  ✅ DNS Resolution: {IOT_ENDPOINT} -> {ip}")
        
        # Port 8883 (MQTT over TLS)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((IOT_ENDPOINT, 8883))
        sock.close()
        
        if result == 0:
            print(f"  ✅ Port 8883 (MQTT/TLS): Reachable")
        else:
            print(f"  ❌ Port 8883 (MQTT/TLS): Cannot connect")
            return False
            
        # Port 443 (HTTPS)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((IOT_ENDPOINT, 443))
        sock.close()
        
        if result == 0:
            print(f"  ✅ Port 443 (HTTPS): Reachable")
        else:
            print(f"  ⚠️  Port 443 (HTTPS): Cannot connect")
        
        return True
        
    except socket.gaierror as e:
        print(f"  ❌ DNS Resolution failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Network check failed: {e}")
        return False

def test_openssl():
    """Test TLS connection using OpenSSL."""
    print(f"\n🔒 Testing TLS connection with OpenSSL...")
    
    cmd = [
        "openssl", "s_client", "-connect", f"{IOT_ENDPOINT}:8883",
        "-cert", PATH_TO_CERT,
        "-key", PATH_TO_KEY,
        "-CAfile", PATH_TO_ROOT,
        "-verify_return_error",
        "-verify", "1",
        "-showcerts"
    ]
    
    try:
        # Run with timeout and capture output
        result = subprocess.run(
            cmd, 
            input="Q\n",  # Send Q to quit
            text=True,
            capture_output=True,
            timeout=10
        )
        
        output = result.stdout + result.stderr
        
        if "Verify return code: 0 (ok)" in output:
            print("  ✅ OpenSSL connection successful")
            return True
        elif "certificate verify failed" in output.lower():
            print("  ❌ Certificate verification failed")
            print("     Check if your certificate is valid and properly attached to IoT policy")
        elif "connection refused" in output.lower():
            print("  ❌ Connection refused - check endpoint and network")
        elif "handshake failure" in output.lower():
            print("  ❌ TLS handshake failed - likely certificate/key mismatch")
        else:
            print(f"  ❌ OpenSSL test failed")
            print(f"     Output snippet: {output[:200]}...")
        
        return False
        
    except subprocess.TimeoutExpired:
        print("  ⚠️  OpenSSL test timed out")
        return False
    except FileNotFoundError:
        print("  ⚠️  OpenSSL not found - install with: sudo yum install openssl")
        return False
    except Exception as e:
        print(f"  ❌ OpenSSL test error: {e}")
        return False

def check_aws_cli():
    """Check if AWS CLI is configured and can access IoT."""
    print(f"\n🔧 Checking AWS CLI configuration...")
    
    try:
        # Check AWS credentials
        result = subprocess.run(["aws", "sts", "get-caller-identity"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            print(f"  ✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        else:
            print("  ❌ AWS CLI not configured or no credentials")
            print("     Run: aws configure")
            return False
        
        # Test IoT endpoint
        result = subprocess.run(["aws", "iot", "describe-endpoint", "--endpoint-type", "iot:Data-ATS"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            endpoint_data = json.loads(result.stdout)
            aws_endpoint = endpoint_data.get('endpointAddress', '')
            print(f"  ✅ AWS IoT Endpoint: {aws_endpoint}")
            
            if aws_endpoint != IOT_ENDPOINT:
                print(f"  ⚠️  Your endpoint ({IOT_ENDPOINT}) doesn't match AWS ({aws_endpoint})")
        else:
            print("  ❌ Cannot access IoT endpoint via AWS CLI")
        
        return True
        
    except Exception as e:
        print(f"  ❌ AWS CLI check failed: {e}")
        return False

def main():
    """Run all diagnostic checks."""
    print("🚀 AWS IoT Connection Diagnostics\n" + "="*50)
    
    # Update this with your actual endpoint
    if "your-endpoint-here" in IOT_ENDPOINT:
        print("❌ Please update IOT_ENDPOINT in this script with your actual endpoint!")
        return
    
    checks = [
        ("Certificate Files", check_files),
        ("Network Connectivity", check_network),
        ("AWS CLI", check_aws_cli),
        ("TLS Connection", test_openssl),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results[name] = False
    
    print("\n" + "="*50)
    print("📋 SUMMARY:")
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    if not results.get("Certificate Files", False):
        print("  🔑 Fix certificate file issues first")
    
    if not results.get("Network Connectivity", False):
        print("  🌐 Check network/firewall settings")
        print("     Ensure ports 8883 and 443 are open")
    
    if not results.get("AWS CLI", False):
        print("  🔧 Configure AWS CLI: aws configure")
    
    if not results.get("TLS Connection", False):
        print("  🔒 Certificate/Policy issues:")
        print("     - Ensure certificate is attached to IoT thing")
        print("     - Verify IoT policy allows iot:Connect, iot:Subscribe, iot:Publish")
        print("     - Check certificate hasn't expired")
    
    if all(results.values()):
        print("  🎉 All checks passed! Your connection should work.")
    else:
        print("  🔧 Fix the failing checks above, then retry your IoT connection.")

if __name__ == "__main__":
    main()
