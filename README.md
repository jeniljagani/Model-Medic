# Model-Medic

Welcome to **Model-Medic**! This repository contains my internship project, which I built to make debugging and diagnosing Machine Learning models a lot easier and more automated. 

## What does it do?

Model-Medic acts as an intelligent diagnosis, explainability, and AI-assistance layer that sits on top of ClearML. When you're training models, a lot can go wrong—from dataset issues (like data leakage, messy distributions, or weird outliers) to training hiccups (like overfitting, underfitting, or unstable metrics).

This project helps by automatically diagnosing these issues. It looks at your ClearML experiments and dataset metrics, and points out exactly what's failing and why, saving you hours of staring at logs and charts. It essentially acts as an automated "medic" for your ML pipeline.

### Core Features:
- **Dataset Intelligence**: Automatically spots data leakage, class imbalances, missing values, duplicates, and multicollinearity in your training data.
- **Model Diagnosis**: Detects overfitting, underfitting, and training stability issues by analyzing your metrics.
- **VSCode Extension**: I've also included a built-in VSCode extension (`modelmedic-vscode`) so you can get dashboards and insights right where you write your code.
- **ClearML Integration**: Natively fetches dataset and experiment telemetry from your ClearML environment to run its analysis.

## How to Install and Use

### Prerequisites
Make sure you have Python (3.9 or newer) installed and a working ClearML workspace configured on your machine (meaning your `clearml.conf` is set up with your credentials).

### 1. Python Package Installation

To install the core Python library, navigate into the project directory and install the requirements:

```bash
git clone https://github.com/jeniljagani/Model-Medic.git
cd Model-Medic/modelmedic
pip install -r requirements.txt
python setup.py install
```

Once installed, you can use the `modelmedic` CLI command or import it into your python scripts to analyze your runs.

### 2. Setting up the VSCode Extension

If you want to use the VSCode extension to view the visual dashboards:

1. Open the `modelmedic-vscode` folder in VSCode.
2. Run `npm install` in your terminal to grab all the dependencies.
3. Hit `F5` (or go to the Run and Debug tab and click "Run Extension"). This will compile the typescript files and open a new VSCode window with the Model-Medic extension loaded!

## A Bit About This Project

I built this during my internship, and it was a massive learning experience! I wanted to tackle the problem of "silent" ML failures—those frustrating moments when your model trains without crashing, but the results are garbage because of some subtle data leak or metric instability. Building a tool that seamlessly integrates with ClearML to catch these issues was super rewarding. I hope it helps you debug your models as much as it helped me learn about ML ops!

---
Feel free to poke around the code, use it for your own ML projects, or open an issue if you have suggestions.
