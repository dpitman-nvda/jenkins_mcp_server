import requests
from typing import Dict, List, Optional, Any, Union
from requests.auth import HTTPBasicAuth

from .config import jenkins_settings


class JenkinsClient:
    """Client for interacting with Jenkins API."""
    
    def __init__(self):
        """Initialize the Jenkins client using configuration settings."""
        try:
            # Disable SSL verification warnings
            import urllib3
            urllib3.disable_warnings()

            self.base_url = jenkins_settings.url.rstrip('/')

            if jenkins_settings.username and (jenkins_settings.token or jenkins_settings.password):
                secret = jenkins_settings.token or jenkins_settings.password
                method = "API token" if jenkins_settings.token else "password"
                print(f"Using {method} authentication for user {jenkins_settings.username}")
                self.auth = HTTPBasicAuth(jenkins_settings.username, secret)
            else:
                print("No credentials configured — running in read-only mode")
                self.auth = None

            # Test connection
            print("\nTesting connection with direct request...")
            response = requests.get(f"{self.base_url}/api/json",
                                 auth=self.auth,
                                 verify=False)
            print(f"Direct request status: {response.status_code}")

            if response.ok:
                print("Direct API call successful!")
                data = response.json()
                print(f"Server version: {data.get('_class', 'unknown')}")

                # Store the initial jobs data
                self._jobs = data.get('jobs', [])
                print(f"Found {len(self._jobs)} jobs:")
                for job in self._jobs:
                    print(f"- {job['name']} ({job.get('color', 'unknown')})")
            else:
                print(f"Direct API call failed: {response.text}")
                raise Exception("Failed to connect to Jenkins")

        except Exception as e:
            print(f"\nError connecting to Jenkins: {str(e)}")
            print("\nPlease check:")
            print(f"1. Jenkins server is running at {jenkins_settings.url}")
            if self.auth:
                print("2. Your credentials in .env file are correct")
                print("3. You have proper permissions in Jenkins")
            else:
                print("2. The Jenkins server allows anonymous read access")
            import traceback
            traceback.print_exc()
            raise
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get a list of all Jenkins jobs."""
        try:
            response = requests.get(f"{self.base_url}/api/json",
                                 auth=self.auth,
                                 verify=False)
            response.raise_for_status()
            return response.json().get('jobs', [])
        except Exception as e:
            print(f"Error getting Jenkins jobs: {str(e)}")
            return []
    
    def get_folder_jobs(self, folder_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get jobs within a specific Jenkins folder."""
        try:
            if folder_path:
                url = f"{self.base_url}/job/{folder_path}/api/json"
            else:
                url = f"{self.base_url}/api/json"
            response = requests.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json().get('jobs', [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Folder '{folder_path}' not found. Use folder notation with /job/ between levels. "
                    f"Example: 'FolderName/job/SubFolder'. Use list-folder-jobs without a path to see top-level items."
                )
            raise
        except Exception as e:
            print(f"Error getting folder jobs for {folder_path}: {str(e)}")
            raise

    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific job."""
        try:
            response = requests.get(f"{self.base_url}/job/{job_name}/api/json",
                                 auth=self.auth,
                                 verify=False)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Job '{job_name}' not found. If this is a nested job, use folder notation: "
                    f"'FolderName/job/SubFolder/job/JobName'. Use the list-folder-jobs tool to browse available jobs."
                )
            raise
        except Exception as e:
            print(f"Error getting job info for {job_name}: {str(e)}")
            raise
    
    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get information about a specific build."""
        try:
            response = requests.get(f"{self.base_url}/job/{job_name}/{build_number}/api/json",
                                 auth=self.auth,
                                 verify=False)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Build #{build_number} for job '{job_name}' not found. If this is a nested job, use folder notation: "
                    f"'FolderName/job/SubFolder/job/JobName'. Use the list-folder-jobs tool to browse available jobs."
                )
            raise
        except Exception as e:
            print(f"Error getting build info for {job_name} #{build_number}: {str(e)}")
            raise
    
    def get_build_console_output(self, job_name: str, build_number: int) -> str:
        """Get console output from a build."""
        try:
            response = requests.get(f"{self.base_url}/job/{job_name}/{build_number}/consoleText",
                                 auth=self.auth,
                                 verify=False)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Console output for build #{build_number} of job '{job_name}' not found. If this is a nested job, use folder notation: "
                    f"'FolderName/job/SubFolder/job/JobName'. Use the list-folder-jobs tool to browse available jobs."
                )
            raise
        except Exception as e:
            print(f"Error getting build console for {job_name} #{build_number}: {str(e)}")
            raise
    
    def build_job(self, job_name: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Trigger a build for a job."""
        try:
            url = f"{self.base_url}/job/{job_name}/build"
            if parameters:
                url = f"{self.base_url}/job/{job_name}/buildWithParameters"
            response = requests.post(url,
                                  auth=self.auth,
                                  params=parameters,
                                  verify=False)
            response.raise_for_status()
            # Get queue item number from Location header
            location = response.headers.get('Location', '')
            queue_id = location.split('/')[-2] if location else None
            return int(queue_id) if queue_id and queue_id.isdigit() else -1
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Job '{job_name}' not found. If this is a nested job, use folder notation: "
                    f"'FolderName/job/SubFolder/job/JobName'. Use the list-folder-jobs tool to browse available jobs."
                )
            raise
        except Exception as e:
            print(f"Error triggering build for {job_name}: {str(e)}")
            raise
    
    def stop_build(self, job_name: str, build_number: int) -> None:
        """Stop a running build."""
        try:
            response = requests.post(f"{self.base_url}/job/{job_name}/{build_number}/stop",
                                  auth=self.auth,
                                  verify=False)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Build #{build_number} for job '{job_name}' not found. If this is a nested job, use folder notation: "
                    f"'FolderName/job/SubFolder/job/JobName'. Use the list-folder-jobs tool to browse available jobs."
                )
            raise
        except Exception as e:
            print(f"Error stopping build {job_name} #{build_number}: {str(e)}")
            raise
    
    def get_queue_info(self) -> List[Dict[str, Any]]:
        """Get information about the queue."""
        try:
            response = requests.get(f"{self.base_url}/queue/api/json",
                                 auth=self.auth,
                                 verify=False)
            response.raise_for_status()
            return response.json().get('items', [])
        except Exception as e:
            print(f"Error getting queue info: {str(e)}")
            return []
    
    def get_node_info(self, node_name: str) -> Dict[str, Any]:
        """Get information about a specific node."""
        try:
            response = requests.get(f"{self.base_url}/computer/{node_name}/api/json",
                                 auth=self.auth,
                                 verify=False)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Node '{node_name}' not found. Check the node name and use the list-nodes tool to see available nodes."
                )
            raise
        except Exception as e:
            print(f"Error getting node info for {node_name}: {str(e)}")
            raise
    
    def get_pipeline_stages(self, job_name: str, build_number: int) -> List[Dict[str, Any]]:
        """Get pipeline stages for a build via the Workflow API."""
        try:
            response = requests.get(
                f"{self.base_url}/job/{job_name}/{build_number}/wfapi/describe",
                auth=self.auth,
                verify=False,
            )
            response.raise_for_status()
            return response.json().get('stages', [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Pipeline data for build #{build_number} of job '{job_name}' not found. "
                    f"This build may not be a Pipeline job, or the job path may be incorrect."
                )
            raise
        except (ValueError, KeyError):
            # Non-pipeline jobs may return non-JSON or unexpected format
            raise Exception(
                "This build does not appear to be a Pipeline job."
            )

    def get_node_log(self, job_name: str, build_number: int, node_id: str) -> Dict[str, Any]:
        """Get the log for a specific pipeline flow node."""
        try:
            response = requests.get(
                f"{self.base_url}/job/{job_name}/{build_number}/execution/node/{node_id}/wfapi/log",
                auth=self.auth,
                verify=False,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Log for node '{node_id}' in build #{build_number} of job '{job_name}' not found. "
                    f"Check that the node ID is valid (use get-failing-stages to list stages)."
                )
            raise
        except (ValueError, KeyError):
            raise Exception(
                "This build does not appear to be a Pipeline job."
            )

    def get_node_describe(self, job_name: str, build_number: int, node_id: str) -> Dict[str, Any]:
        """Get the wfapi describe for a specific pipeline flow node, including child stageFlowNodes."""
        try:
            response = requests.get(
                f"{self.base_url}/job/{job_name}/{build_number}/execution/node/{node_id}/wfapi/describe",
                auth=self.auth,
                verify=False,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Node '{node_id}' in build #{build_number} of job '{job_name}' not found."
                )
            raise
        except (ValueError, KeyError):
            raise Exception(
                "This build does not appear to be a Pipeline job."
            )

    # Keep old name as alias for backwards compatibility
    def get_stage_log(self, job_name: str, build_number: int, stage_id: str) -> Dict[str, Any]:
        """Get the log for a specific pipeline stage (alias for get_node_log)."""
        return self.get_node_log(job_name, build_number, stage_id)

    def get_nodes(self) -> List[Dict[str, str]]:
        """Get a list of all nodes."""
        try:
            response = requests.get(f"{self.base_url}/computer/api/json",
                                 auth=self.auth,
                                 verify=False)
            response.raise_for_status()
            return response.json().get('computer', [])
        except Exception as e:
            print(f"Error getting nodes: {str(e)}")
            return []


# Create a singleton instance
jenkins_client = JenkinsClient()
