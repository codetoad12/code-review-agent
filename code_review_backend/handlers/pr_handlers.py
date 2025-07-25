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
    def __init__(self, repo_owner: str, repo_name: str, pr_number: int):
        self.authentication_token = os.getenv("GITHUB_TOKEN")
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
    def __init__(self, repo_owner: str, repo_name: str, pr_number: int):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.github_client = GithubClient(self.repo_owner, self.repo_name, self.pr_number)

    def format_pr_info(self, pr_info: dict):
        # import ipdb; ipdb.set_trace()
        return {
            "pr_number": pr_info["number"],
            "pr_title": pr_info["title"],
            "pr_body": pr_info["body"],
            "pr_created_at": pr_info["created_at"],
            "pr_updated_at": pr_info["updated_at"],
            "language": pr_info['base']['repo']['language'],
            "state": pr_info["state"],
            "author_association": pr_info["author_association"],
            "stats":{
                "commits": pr_info["commits"],
                "comments": pr_info["comments"],
                "additions": pr_info["additions"],
                "deletions": pr_info["deletions"],
                "changed_files": pr_info["changed_files"],
                "review_comments": pr_info["review_comments"],
            }
        }

    def format_pr_files(self, file_info: dict):
        pass

    def format_pr_comments(self, comments: dict):
        if comments:
            return {
                'file':comments['path'],    
                'line':comments['line'],
                'comment':comments['body'],
                'author':comments['user']['login'],
                'author_association':comments['author_association'],
            }
        return []

    def format_pr_commits(self, commits: dict):
        commit_list = []
        if commits:
            for commit in commits:
                commit_list.append(commit['commit']['message'])
            return commit_list
        return []
    
    def format_file_info(self, file_info: dict):
        file_list = []
        if file_info:
            for file in file_info:
                file_list.append({
                    'file_name':file['filename'],
                    'additions':file['additions'],
                    'deletions':file['deletions'],
                    'changes':file['changes'],
                    'patch':file['patch'],
                    'status':file['status'],
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
        reviews = self.github_client.get_pr_reviews()

        final_payload = self.create_final_payload(pr_info, file_info, comments, commits, reviews)
        return final_payload

