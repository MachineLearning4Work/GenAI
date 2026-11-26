variable "project_root" {
  # Docker Compose mounts the project at /workspace; this value points there.
  description = "Absolute path to the root of this teaching project."
  type        = string
}

variable "run_name" {
  # Changing this value creates a separate output directory for the run.
  description = "Name of the ML run and output subdirectory."
  type        = string
}

variable "python_command" {
  # Keep this configurable so the same module can use another Python executable.
  description = "Python executable used to run the ML job."
  type        = string
  default     = "python3"
}
