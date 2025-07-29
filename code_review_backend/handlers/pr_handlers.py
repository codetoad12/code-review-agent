import httpx
import os


class GithubEndpoint:
    def __init__(self, pr_number: int, repo_owner: str, repo_name: str):
        self.pr_number = pr_number
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pr_endpoint = "/pulls"
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.pr_comments_endpoint = f"/pulls/{pr_number}/comments"
        self.pr_files_endpoint = f"/pulls/{pr_number}/files"
        self.pr_commits_endpoint = f"/pulls/{pr_number}/commits"
        self.pr_reviews_endpoint = f"/pulls/{pr_number}/reviews"

    def get_pr_endpoint(self):
        return f"{self.base_url}/pulls/{self.pr_number}"
    
    def get_pr_comments_endpoint(self):
        return f"{self.base_url}{self.pr_comments_endpoint}"
    
    def get_pr_files_endpoint(self):
        return f"{self.base_url}{self.pr_files_endpoint}"

    def get_pr_commits_endpoint(self):
        return f"{self.base_url}{self.pr_commits_endpoint}"
    
    def get_pr_reviews_endpoint(self):
        return f"{self.base_url}{self.pr_reviews_endpoint}"

class GithubClient:
    def __init__(self, repo_owner: str, repo_name: str, pr_number: int, github_token: str = None):
        # Use provided token or fall back to environment variable
        self.authentication_token = github_token or os.getenv("GITHUB_TOKEN")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.endpoint = GithubEndpoint(pr_number, self.repo_owner, self.repo_name)
    
    def _get_headers(self):
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.authentication_token:
            headers["Authorization"] = f"Bearer {self.authentication_token}"
        return headers

    def _make_request(self, url: str, error_message: str, params: dict = None):
        """Helper method to make HTTP requests with common error handling."""
        try:
            response = httpx.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"{error_message}: {str(e)}"}

    def get_pr(self):
        url = self.endpoint.get_pr_endpoint()
        return self._make_request(url, "Failed to fetch PR")

    def get_pr_comments(self):
        url = self.endpoint.get_pr_comments_endpoint()
        return self._make_request(url, "Failed to fetch PR comments")

    def get_pr_files(self):
        url = self.endpoint.get_pr_files_endpoint()
        return self._make_request(
            url, "Failed to fetch PR files", params={"per_page": 100}
        )

    def get_pr_commits(self):
        url = self.endpoint.get_pr_commits_endpoint()
        return self._make_request(url, "Failed to fetch PR commits")
    
    def get_pr_reviews(self):
        url = self.endpoint.get_pr_reviews_endpoint()
        return self._make_request(url, "Failed to fetch PR reviews")

class GithubPrHandler:
    def __init__(self, repo_owner: str, repo_name: str, pr_number: int, github_token: str = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.github_client = GithubClient(self.repo_owner, self.repo_name, self.pr_number, github_token)

    def format_pr_info(self, pr_info):
        print(pr_info)
        # Check if the response contains an error
        if isinstance(pr_info, dict) and 'error' in pr_info:
            print(f"Error fetching PR info: {pr_info['error']}")
            raise Exception(f"Failed to fetch PR info: {pr_info['error']}")
        
        # Safely extract nested language information
        base_obj = pr_info.get('base') or {}
        repo_obj = base_obj.get('repo') if isinstance(base_obj, dict) else {}
        language = repo_obj.get('language', '') if isinstance(repo_obj, dict) else ''
        
        return {
            "pr_number": pr_info.get("number", 0),
            "pr_title": pr_info.get("title", ""),
            "pr_body": pr_info.get("body", ""),
            "pr_created_at": pr_info.get("created_at", ""),
            "pr_updated_at": pr_info.get("updated_at", ""),
            "language": language,
            "state": pr_info.get("state", ""),
            "author_association": pr_info.get("author_association", ""),
            "stats":{
                "commits": pr_info.get("commits", 0),
                "comments": pr_info.get("comments", 0),
                "additions": pr_info.get("additions", 0),
                "deletions": pr_info.get("deletions", 0),
                "changed_files": pr_info.get("changed_files", 0),
                "review_comments": pr_info.get("review_comments", 0),
            }
        }

    def format_pr_files(self, file_info: dict):
        pass

    def format_pr_comments(self, comments):
        comment_list = []
        # Check if the response contains an error
        if isinstance(comments, dict) and 'error' in comments:
            print(f"Error fetching comments: {comments['error']}")
            return []
        
        if comments and isinstance(comments, list):
            for comment in comments:
                # Safely handle nested user object
                user_obj = comment.get('user') or {}
                author_login = user_obj.get('login', '') if isinstance(user_obj, dict) else ''
                
                comment_list.append({
                    'file': comment.get('path', ''),    
                    'line': comment.get('line', 0),
                    'comment': comment.get('body', ''),
                    'author': author_login,
                    'author_association': comment.get(
                        'author_association', ''
                    ),
                })
            return comment_list
        return []

    def format_pr_commits(self, commits):
        commit_list = []
        # Check if the response contains an error
        if isinstance(commits, dict) and 'error' in commits:
            print(f"Error fetching commits: {commits['error']}")
            return []
        
        if commits and isinstance(commits, list):
            for commit in commits:
                # Safely handle nested commit object
                commit_obj = commit.get('commit') or {}
                message = commit_obj.get('message', '') if isinstance(commit_obj, dict) else ''
                if message:
                    commit_list.append(message)
            return commit_list
        return []
    
    def format_file_info(self, file_info):
        file_list = []
        # Check if the response contains an error
        if isinstance(file_info, dict) and 'error' in file_info:
            print(f"Error fetching files: {file_info['error']}")
            return []
        
        if file_info and isinstance(file_info, list):
            for file in file_info:
                file_list.append({
                    'file_name': file.get('filename', ''),
                    'additions': file.get('additions', 0),
                    'deletions': file.get('deletions', 0),
                    'changes': file.get('changes', 0),
                    'patch': file.get('patch', ''),
                    'status': file.get('status', ''),
                })
            return file_list
        return []

    def create_final_payload(self, pr_info: dict, file_info: dict, comments: dict, commits: dict, reviews: dict):
        return {
            "summary": {**pr_info,  'commits':commits},
            "file_info": file_info,
            "existing_reviews":reviews,
            "existing_comments":comments,
        }
    
    def format_pr_data_to_pass_to_agent(self):
        pr_info = self.format_pr_info(self.github_client.get_pr())
        file_info = self.format_file_info(self.github_client.get_pr_files())
        comments = self.format_pr_comments(
            self.github_client.get_pr_comments()
        )
        commits = self.format_pr_commits(self.github_client.get_pr_commits())
        
        # Handle reviews data with error checking
        reviews_data = self.github_client.get_pr_reviews()
        if isinstance(reviews_data, dict) and 'error' in reviews_data:
            print(f"Error fetching reviews: {reviews_data['error']}")
            reviews = []
        else:
            reviews = reviews_data if reviews_data else []

        final_payload = self.create_final_payload(
            pr_info, file_info, comments, commits, reviews
        )
        return final_payload