# Attendance Report System

A Python-based automated system for parsing, transforming, and generating attendance reports (supporting Type A and Type B formats) with a robust layered architecture, design patterns, and comprehensive unit testing.

---

## Project Structure & Architecture

The project is built using a clean, layered architecture separating concerns into distinct modules:
- **`domain/`**: Contains core data models (`AttendanceReport`, `AttendanceRow`, `ReportSummary`).
- **`parsers/`**: Implements parsing logic for extracting raw attendance data from input files (Type A and Type B parsers).
- **`transformation/`**: Implements transformation strategies (Strategy Pattern) to process and normalize report data.
- **`generators/`**: Responsible for generating final formatted outputs (such as HTML reports).
- **`tests/`**: Contains the complete `pytest` test suite covering normal operations and edge cases.
- **`main.py` & `cli.py`**: Entry points for executing the application workflow.

---

## Running the Project with Docker

To ensure that anyone can run this project easily and consistently on any machine without manually installing dependencies, you can use Docker.

### Prerequisites
- Make sure you have [Docker](https://docs.docker.com/get-docker/) installed and running on your system.

### Step-by-Step Instructions

1. **Clone or Download the Project:**
   Open your terminal in the root directory of the project (where the `Dockerfile` and `requirements.txt` are located).

2. **Build the Docker Image:**
   Run the following command in your terminal to build the container image:
   ```bash
   docker build -t attendance-system .