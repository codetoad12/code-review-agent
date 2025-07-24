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

    def get_pr_endpoint(self, pr_number: int):
        return f"{self.base_url}/pulls/{pr_number}"
    
    def get_pr_comments_endpoint(self):
        return f"{self.base_url}{self.pr_comments_endpoint}"
    
    def get_pr_files_endpoint(self):
        return f"{self.base_url}{self.pr_files_endpoint}"


class GithubClient:
    def __init__(self, repo_owner: str, repo_name: str):
        self.authentication_token = os.getenv("GITHUB_TOKEN")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        
    def _get_headers(self):
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.authentication_token:
            headers["Authorization"] = f"Bearer {self.authentication_token}"
        return headers

    def get_pr(self, pr_number: int):
        endpoint = GithubEndpoint(pr_number, self.repo_owner, self.repo_name)
        url = endpoint.get_pr_endpoint(pr_number)
        
        try:
            response = httpx.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"Failed to fetch PR: {str(e)}"}

    def get_pr_comments(self, pr_number: int):
        endpoint = GithubEndpoint(self.base_url, pr_number, self.repo_owner, self.repo_name)
        url = endpoint.get_pr_comments_endpoint()
        
        try:
            response = httpx.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"Failed to fetch PR comments: {str(e)}"}


class GithubPrHandler:
    def __init__(self, repo_owner: str, repo_name: str, pr_number: int):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.github_client = GithubClient(self.repo_owner, self.repo_name)

    def get_pr_info(self):
        pr = self.github_client.get_pr(self.pr_number)
        return pr

    def get_pr_comments(self, pr_number: int):
        comments = self.github_client.get_pr_comments(pr_number)
        return comments