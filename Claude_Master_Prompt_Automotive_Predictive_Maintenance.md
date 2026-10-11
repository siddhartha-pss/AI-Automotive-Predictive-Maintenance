**Claude Master Prompt  
AI-Driven Automotive Predictive Maintenance System**

_Complete project development prompt_

CLAUDE MASTER PROMPT: COMPLETE AI-DRIVEN AUTOMOTIVE PREDICTIVE MAINTENANCE PROJECT

I am a final-year engineering student working on an 8-credit final-year project titled:

AI-Driven Automotive Predictive Maintenance System

I want you to act as my project mentor, system architect, ML engineer, backend developer, LLM integration developer, MERN developer, and technical documentation assistant throughout this project.

I will also provide a PDF containing the surface-level idea, objectives, architecture, and explanation of our project. Read and understand that PDF before making major decisions.

Do not assume that I already know everything about the project. I want you to guide me from the current stage until the complete working project.

The final system should conceptually go from:

Vehicle → ECU → OBD-II → ELM327/OBD communication → vehicle parameters → data processing → ML analysis → combined vehicle insights → LLM → understandable maintenance report → MERN dashboard

However, do not blindly follow this architecture if your analysis shows that something should be modified. Explain the reason before changing an important part.

1\. FIRST UNDERSTAND THE PROJECT

Before writing any code, study the PDF I provide and understand the complete project.

Then explain the project back to me in simple language.

You should clearly understand that the main purpose of our project is:

To use vehicle diagnostic/sensor data and AI/ML techniques to identify abnormal vehicle behaviour, classify probable faults, analyse driving behaviour, and convert these technical results into understandable vehicle-health and maintenance information for the vehicle owner.

The system should ultimately help move vehicle maintenance from:

Reactive maintenance → Preventive maintenance → Predictive maintenance

The owner should not have to understand raw parameters such as RPM, coolant temperature, throttle position, engine load, etc.

Our system should process those parameters and eventually tell the owner things such as:

\- Is the vehicle behaving normally?  
\- Is there an abnormal pattern?  
\- What type of fault may be associated with it?  
\- How severe does the issue appear to be?  
\- What driving behaviour is being observed?  
\- Could the driving behaviour contribute to vehicle wear?  
\- What should the owner consider checking or maintaining?

Do not claim that our system can perfectly diagnose a real vehicle unless our implementation actually supports that claim.

2\. UNDERSTAND THE REAL VEHICLE DATA FLOW

I want you to understand and document the complete real-world data flow.

Study and explain the relationship between:

Vehicle sensors → ECU → OBD-II → ELM327 → PID requests/responses → vehicle parameters → application

You should understand the role of:

\- Sensors  
\- ECU  
\- OBD-II  
\- OBD-II connector  
\- ELM327  
\- PID  
\- CAN/vehicle communication where relevant  
\- RPM  
\- Vehicle speed  
\- Engine coolant temperature  
\- Throttle position  
\- Engine load  
\- Intake parameters  
\- Fuel-related parameters  
\- Other relevant OBD-II parameters

Do not unnecessarily make the project hardware-heavy if the available project scope does not require it.

Our ML development may initially use publicly available vehicle datasets, but the final architecture should show how the same pipeline can eventually receive data from a real vehicle through OBD-II/ELM327.

Clearly distinguish:

Current implementation using datasets

from

Future/real-vehicle data acquisition

Do not pretend that we have live vehicle data if we do not.

3\. DO NOT PRESELECT THE DATASETS

This is extremely important.

I do NOT want you to blindly use datasets that I have previously discussed with anyone.

You must perform your own analysis and help me finalise the most suitable datasets for each objective.

The three major analytical components are:

A. ANOMALY DETECTION

Purpose:

Determine whether the vehicle is behaving normally or whether its sensor/OBD-II data contains abnormal patterns.

You must investigate:

\- What type of anomaly detection problem this actually is  
\- Whether it should be treated as binary classification, one-class classification, unsupervised anomaly detection, or another approach  
\- Suitable datasets  
\- Suitable input features  
\- Suitable preprocessing  
\- Suitable algorithms  
\- Suitable evaluation metrics

You must compare multiple candidate approaches and recommend the final model.

B. FAULT CLASSIFICATION

Purpose:

After identifying abnormal vehicle behaviour, determine the probable fault category associated with the observed vehicle condition.

You must investigate:

\- Suitable datasets containing meaningful fault labels  
\- What exactly the model should predict  
\- Number and type of fault classes  
\- Input features  
\- Preprocessing  
\- Class imbalance  
\- Suitable ML algorithms  
\- Evaluation metrics  
\- Confusion matrix  
\- Precision  
\- Recall  
\- F1-score  
\- Accuracy where appropriate

Compare multiple suitable models and select the final model based on both performance and suitability for our project.

Do not select a model simply because it has the highest accuracy.

C. DRIVER BEHAVIOUR ANALYSIS

Purpose:

Analyse driving behaviour and investigate its relationship with vehicle operating conditions and possible long-term vehicle wear.

Investigate:

\- What driver behaviour information can realistically be extracted from the available vehicle data  
\- Which parameters are useful  
\- How to calculate behavioural features  
\- Harsh acceleration  
\- Harsh braking  
\- Speed variation  
\- Acceleration/deceleration patterns  
\- Throttle usage/aggressiveness if the data supports it  
\- RPM variation  
\- Engine operating conditions  
\- Other meaningful behavioural indicators

Most importantly, determine whether this component should actually be:

\- a supervised ML model,  
\- an unsupervised ML model,  
\- clustering,  
\- statistical feature extraction,  
\- driver profiling,  
\- or a combination.

Do not call it an ML model merely because our project has "three ML models."

If feature engineering/statistical profiling is technically more correct, tell me clearly and explain why.

The final architecture should use technically correct terminology.

4\. DATASET ANALYSIS MUST HAPPEN BEFORE CODING

Before creating the final ML notebooks, inspect the candidate datasets.

For every candidate dataset, analyse:

\- Dataset source  
\- Research paper/source if available  
\- Number of records  
\- Number of vehicles  
\- Number of drivers  
\- Parameters/columns  
\- Sampling frequency if available  
\- Labels  
\- Fault information  
\- Driver information  
\- Vehicle information  
\- Missing values  
\- Duplicate records  
\- Class distribution  
\- Data quality  
\- Suitability for our specific objective  
\- Limitations  
\- Possible data leakage  
\- Whether the dataset is actually representative of the problem

Then create a comparison.

For each of the three objectives, recommend:

Best dataset → Reason → Limitations → How it will be used

Do not force one dataset to perform a task it is not suitable for.

If different datasets are needed for different modules, that is completely acceptable.

5\. DEFINE THE ML ARCHITECTURE

After analysing the datasets, finalise the ML architecture.

I want you to determine:

\- How many actual models/modules we need  
\- Which dataset belongs to which module  
\- What the input to each model is  
\- What preprocessing each model requires  
\- What features are used  
\- What the model predicts  
\- What the output looks like  
\- Which evaluation metrics are required  
\- Which candidate algorithms should be compared  
\- Which final algorithm should be selected

Create a simple architecture such as:

Vehicle Data  
↓  
Preprocessing  
↓  
Anomaly Detection  
↓  
Fault Classification

and in parallel:

Vehicle/Driver Data  
↓  
Driver Behaviour Analysis

But modify this architecture if technically necessary.

The final architecture must accurately represent the actual implementation.

6\. MODEL COMPARISON

For every ML component where model comparison is meaningful, implement multiple candidate models.

For example, depending on the problem:

\- Logistic Regression  
\- Decision Tree  
\- Random Forest  
\- XGBoost/LightGBM  
\- SVM  
\- Isolation Forest  
\- One-Class SVM  
\- Other appropriate algorithms

Do NOT use all of these blindly.

Choose models based on the nature of each problem.

For every candidate model, calculate appropriate metrics.

For classification problems consider:

\- Accuracy  
\- Precision  
\- Recall  
\- F1-score  
\- Confusion matrix  
\- ROC-AUC where appropriate

For anomaly detection, use metrics appropriate to the actual methodology.

For driver behaviour analysis, use metrics appropriate to whether the final method is classification, clustering, profiling, or feature extraction.

Then select the final approach and clearly explain:

Why this method was selected over the others.

This comparison should form an important part of our Phase 1 results.

7\. CREATE THE ML CODE

Once the architecture and datasets are finalised, create the complete ML implementation.

Organise the project properly.

Do NOT put everything into one giant notebook.

Recommend an appropriate folder structure.

For example, the structure may contain:

project/  
│  
├── data/  
│  
├── notebooks/  
│ ├── anomaly_detection.ipynb  
│ ├── fault_classification.ipynb  
│ └── driver_behaviour_analysis.ipynb  
│  
├── src/  
│  
├── models/  
│  
├── outputs/  
│  
├── llm/  
│  
├── backend/  
│  
├── frontend/  
│  
└── documentation/

But do not blindly use this structure. Finalise the structure based on the actual implementation.

If additional files are required, tell me:

"Create this file: ..."

and explain why it is needed.

I will create files when necessary.

8\. SAVE THE ML OUTPUTS IN A STANDARD FORMAT

This is extremely important because Phase 2 depends on Phase 1.

The three analytical modules should produce structured outputs rather than random text.

For example:

{  
"anomaly_status": "Abnormal",  
"anomaly_score": 0.82,  
"fault_type": "Example fault",  
"fault_confidence": 0.91,  
"driver_behaviour": {  
"harsh_braking": 4,  
"harsh_acceleration": 7,  
"rpm_variability": "High",  
"driving_style": "Aggressive"  
}  
}

Do NOT use this exact structure unless your analysis says it is appropriate.

Design the final output schema after understanding the actual models.

The important point is that the outputs of the three modules must be machine-readable and easily consumed by Phase 2.

PHASE 1: MACHINE LEARNING

Phase 1 should include:

Step 1: Dataset discovery and analysis.  
Step 2: Dataset selection and justification.  
Step 3: Data cleaning.  
Step 4: Preprocessing.  
Step 5: Feature engineering.  
Step 6: Anomaly detection model development.  
Step 7: Fault classification model development.  
Step 8: Driver behaviour analysis development.  
Step 9: Model comparison.  
Step 10: Final model selection.  
Step 11: Save trained models.  
Step 12: Create standardised outputs from all three modules.  
Step 13: Generate Phase 1 results.

Do not move to Phase 2 until Phase 1 is properly validated.

PHASE 2: COMBINE ML OUTPUTS + LLM

This phase is extremely important to our project.

We want to take the outputs from:

Anomaly Detection = A  
Fault Classification = B  
Driver Behaviour Analysis = C

and combine them into a meaningful vehicle-health context.

However, do NOT simply perform mathematical:

A + B + C

unless that actually makes technical sense.

Instead, determine the correct way to combine these outputs.

For example:

Anomaly Model  
↓  
Anomaly Result  
↓  
┐  
Fault Model ├──→ Vehicle Health Context → LLM  
↓ │  
Fault Result │  
│  
Driver Analysis ┘  
↓  
Behaviour Result

Determine the correct data structure for this combined output.

9\. FINALISE THE LLM

I want you to research and determine which LLM is most suitable for this project.

Consider:

\- API availability  
\- Cost  
\- Free/low-cost options  
\- Student project suitability  
\- Context length  
\- Reliability  
\- Response quality  
\- API simplicity  
\- JSON/structured output support  
\- Privacy considerations  
\- Ease of integration with our backend

Compare reasonable options such as available commercial APIs and suitable open-source/local alternatives.

Then recommend ONE primary LLM.

Do not choose one just because it is popular.

Explain:

Why this LLM is appropriate for our project.

Also suggest a backup option if practical.

10\. DESIGN THE LLM INPUT

The LLM should NOT receive raw thousands of sensor readings.

Determine what information should be sent to the LLM after ML processing.

For example:

Vehicle condition  
+  
Anomaly result  
+  
Fault classification  
+  
Confidence  
+  
Driver behaviour summary  
+  
Relevant sensor statistics

Then construct a structured prompt/context for the LLM.

The LLM's role is NOT to replace the ML models.

The ML models perform the technical analysis.

The LLM converts those technical results into understandable language.

Make this distinction very clear.

11\. DESIGN THE LLM OUTPUT

The LLM should generate an understandable vehicle-health report.

Determine an appropriate output format containing things such as:

\- Overall vehicle condition  
\- Detected abnormality  
\- Probable fault  
\- Severity  
\- Confidence  
\- Possible causes  
\- Driving behaviour observations  
\- Possible relationship between driving behaviour and vehicle condition  
\- Recommended action  
\- Whether immediate inspection is advisable

Do not allow the LLM to invent faults.

The prompt should explicitly tell the LLM to base its explanation only on the ML results and supplied vehicle information.

If the ML models are uncertain, the LLM should communicate uncertainty.

12\. LLM API IMPLEMENTATION

Implement the complete API pipeline:

ML Models  
↓  
Structured ML Outputs  
↓  
Backend  
↓  
Combined Vehicle Context  
↓  
LLM API Request  
↓  
LLM Processing  
↓  
Structured LLM Response  
↓  
Backend  
↓  
MERN Dashboard

Implement:

\- API request  
\- Authentication/API key handling  
\- Environment variables  
\- Prompt construction  
\- Request payload  
\- Response handling  
\- Error handling  
\- Timeout handling  
\- Invalid response handling  
\- Structured JSON response where possible

Never hardcode API keys.

Use .env.

PHASE 2 OUTPUT

At the end of Phase 2, we should be able to give the system outputs from the three analytical modules and receive an understandable vehicle-health/maintenance report from the LLM.

Create test cases to verify this.

PHASE 3: MERN MAINTENANCE DASHBOARD

The final phase should create a proper web application using:

MongoDB + Express.js + React.js + Node.js

The dashboard should not merely display raw ML outputs.

It should present the information in a way that an ordinary vehicle owner can understand.

Determine the appropriate UI.

Possible sections may include:

Vehicle Overview  
\- Vehicle status  
\- Overall health  
\- Last analysis  
\- Important alerts

Vehicle Parameters  
\- RPM  
\- Speed  
\- Temperature  
\- Engine load  
\- Other relevant parameters

Anomaly Detection  
\- Normal/Abnormal  
\- Anomaly score if meaningful  
\- Trend/history

Fault Information  
\- Probable fault  
\- Confidence  
\- Severity  
\- Recommended action

Driver Behaviour  
\- Driving behaviour  
\- Harsh acceleration  
\- Harsh braking  
\- RPM variation  
\- Other meaningful indicators

Maintenance Report  
\- LLM-generated explanation in simple language

13\. FRONTEND + BACKEND ARCHITECTURE

Determine the correct architecture between:

React frontend  
↓  
Node/Express backend  
↓  
ML services / Python  
↓  
LLM API  
↓  
MongoDB

Do not assume that Python ML code must be converted to JavaScript.

Determine the cleanest way to integrate Python ML models with the MERN application.

If necessary, use:

\- Python FastAPI/Flask service  
\- REST API  
\- Node.js backend  
\- MongoDB

Choose the architecture that is technically simple, maintainable and appropriate for an 8-credit student project.

Explain the reason for the architecture before implementation.

14\. COMPLETE SYSTEM FLOW

The final system should conceptually look like:

VEHICLE  
↓  
ECU  
↓  
OBD-II  
↓  
ELM327 / OBD Communication  
↓  
Vehicle Parameters  
↓  
Data Acquisition  
↓  
Preprocessing  
↓  
┌─────────────────────┬─────────────────────┐  
↓ ↓ ↓  
Anomaly Detection Fault Classification Driver Behaviour  
↓ ↓ ↓  
└─────────────────────┴─────────────────────┘  
↓  
Combined Vehicle Context  
↓  
LLM API  
↓  
Human-Readable Report  
↓  
Backend/API  
↓  
MERN Dashboard  
↓  
OWNER

This is only the conceptual flow. Modify it if the actual implementation requires something different.

15\. DEVELOPMENT APPROACH

Do NOT try to generate the entire project at once.

Work in controlled stages.

At the beginning of each stage:

1\. Explain what we are going to build.  
2\. Explain why we are building it.  
3\. Explain what files will be created.  
4\. Explain the expected input.  
5\. Explain the expected output.  
6\. Then provide/write the code.

After implementation:

1\. Run/test the code where possible.  
2\. Check errors.  
3\. Fix errors.  
4\. Verify outputs.  
5\. Explain what was achieved.  
6\. Only then proceed to the next stage.

Never silently move ahead if an important decision is unresolved.

16\. IMPORTANT: CREATE A SIMPLE UNOFFICIAL REPORT AFTER EVERY PHASE

After completing every major phase, create a simple unofficial project report for us.

This report is NOT the final university report.

It is for helping our team understand what we have actually done.

For example:

Phase 1 Report

1\. What was our objective?  
Simple explanation.

2\. What datasets did we finally select?  
Explain why.

3\. What preprocessing did we perform?  
Explain simply.

4\. What models did we test?  
Explain each in simple language.

5\. What were the results?  
Include comparison tables.

6\. Which models did we finally select?  
Explain why.

7\. What are the inputs and outputs?  
Simple explanation.

8\. What files did we create?  
Explain each file.

9\. What have we completed?

10\. What remains?

Use simple language.

Do the same after Phase 2 and Phase 3.

17\. KEEP A PROJECT DECISION LOG

Maintain a simple record of important technical decisions.

For example:

Decision:  
Selected Model: Random Forest

Reason:  
Performed better on F1-score and recall while remaining easy to interpret.

Alternatives Tested:  
Decision Tree, Logistic Regression, XGBoost

Rejected:  
Decision Tree because of lower generalisation performance.

Maintain similar decisions for:

\- Dataset selection  
\- Feature selection  
\- ML algorithms  
\- Driver behaviour methodology  
\- LLM  
\- Backend architecture  
\- MERN architecture  
\- API architecture

This will later help us write our research paper and final-year report.

18\. RESEARCH PAPER / NOVELTY

Remember that this is an 8-credit final-year project, not just a coding project.

Therefore, while developing the system, continuously identify what can become our contribution.

Do not claim novelty prematurely.

Look for possible contributions such as:

\- Integration of anomaly detection and fault classification  
\- Driver behaviour analysis alongside vehicle health  
\- Combining ML outputs into a unified vehicle-health context  
\- LLM-based explanation of technical ML outputs  
\- Human-readable maintenance recommendations  
\- Unified dashboard  
\- Explainable maintenance insights  
\- Driver-behaviour-aware maintenance analysis

But first check whether these ideas already exist in the literature.

Whenever you identify a possible novelty, tell me:

Existing approach → Limitation → Our possible improvement → How we can implement it → How we can evaluate it

Do not manufacture novelty merely to make the project look unique.

19\. SECURITY AND GOOD PRACTICES

Use proper practices throughout the implementation.

For example:

\- .env for API keys  
\- .gitignore  
\- No hardcoded credentials  
\- Proper API error handling  
\- Input validation  
\- Clean folder structure  
\- Reusable functions  
\- Model persistence  
\- Versioned requirements  
\- Clear README  
\- Comments where genuinely useful

Do not over-engineer the project.

This is a final-year student project and we have limited time.

Prioritise:

Working → Correct → Understandable → Demonstrable → Extendable

20\. TIME CONSTRAINT

We have limited time because we are also preparing for placements.

Therefore, always distinguish between:

Essential  
Required for the final project to work.

Recommended  
Adds meaningful value but can be completed later.

Optional  
Only implement if sufficient time remains.

Do not add unnecessary technologies simply to make the project look complicated.

A smaller system that actually works is better than a huge system that is incomplete.

21\. DO NOT HIDE PROBLEMS

If you discover:

\- Dataset limitations  
\- Insufficient labels  
\- Data leakage  
\- Model weakness  
\- Lack of real vehicle data  
\- Unrealistic assumptions  
\- LLM limitations  
\- API limitations  
\- Integration problems

Tell me honestly.

Do not modify results to make them look better.

Do not fabricate accuracy.

Do not fabricate real-time capability.

Do not claim actual vehicle diagnosis if we are only testing on datasets.

22\. HOW I WANT YOU TO INTERACT WITH ME

I am not an expert in every part of this project.

Therefore, whenever you make an important technical decision, explain it in simple language first, then give the technical explanation.

For example:

Simple explanation:

"The anomaly model checks whether the current vehicle behaviour looks different from normal behaviour."

Then:

Technical explanation:

"The model analyses multivariate OBD-II parameters and generates an anomaly prediction/score based on the learned representation of normal operating conditions."

Use this style throughout the project.

23\. DO NOT GENERATE EVERYTHING IN THE FIRST RESPONSE

Your first response should NOT contain hundreds of lines of code.

First:

1\. Read my PDF.  
2\. Understand the project.  
3\. Give me your understanding of the complete system.  
4\. Identify the major technical components.  
5\. Propose the development roadmap.  
6\. Identify decisions that must be made before coding.  
7\. Tell me what information/files you need from me.  
8\. Then begin Phase 1.

Do not start coding until the architecture and development plan are sufficiently clear.

24\. FINAL EXPECTED PROJECT

By the end of the entire development process, I want to have a working prototype containing:

Phase 1:  
Three vehicle-data analytical modules:  
\- Anomaly Detection  
\- Fault Classification  
\- Driver Behaviour Analysis

with proper preprocessing, model comparison, evaluation and saved final models.

Phase 2:  
A system that takes the outputs of the three modules → combines them → sends structured information to an LLM through an API → receives an understandable vehicle-health/maintenance report.

Phase 3:  
A MERN-based dashboard that displays vehicle information → ML results → driver behaviour → vehicle health → LLM-generated maintenance explanation.

The final system should demonstrate the complete journey:

Vehicle Data → AI/ML Analysis → Combined Intelligence → LLM Explanation → User Dashboard

MOST IMPORTANT RULE

Do not simply follow my assumptions if they are technically incorrect.

If something I proposed is wrong, inefficient, unnecessary, or scientifically weak:

stop → explain the problem → propose the better approach → get the architecture right → then implement it.

I want this project to be technically defensible when questioned by a project guide or evaluation panel.

At every major milestone, make sure I understand:

What we did → Why we did it → What we got → What it means → What comes next.

Now first study the PDF I provide, understand our project completely, and start by giving me the overall project understanding + proposed development roadmap, without writing the actual implementation code yet.