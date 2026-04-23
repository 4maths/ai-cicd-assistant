import requests
import sys

def test_fetch_public_diff():
    # Sử dụng một PR công khai bất kỳ để test (ví dụ PR #6700 của psf/requests)
    repo = "psf/requests"
    pr_number = 6700
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    
    headers = {
        "Accept": "application/vnd.github.diff"
    }
    
    print(f"Testing GitHub API Diff Fetching for {repo} PR #{pr_number}...")
    try:
        response = requests.get(url, headers=headers, timeout=20)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            diff_content = response.text
            print(f"Successfully fetched diff! Length: {len(diff_content)} characters")
            print("--- DIFF PREVIEW (First 5 lines) ---")
            lines = diff_content.splitlines()[:5]
            for line in lines:
                print(line)
            print("------------------------------------")
            return True
        else:
            print(f"Failed to fetch diff. Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"Error occurred: {e}")
        return False

if __name__ == "__main__":
    success = test_fetch_public_diff()
    sys.exit(0 if success else 1)
