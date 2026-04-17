# endemo





A sector-spanning bottom-up model for long-term energy demand modelling.



### TABLE OF CONTENTS



1. What is endemo
2. How to Install
3. Model Structure and Logic
4. How to Create Your Own Model
5. License, Dataset and Copyright
6. Citations







### 1\. WHAT IS ENDEMO



endemo is a bottom-up energy demand model for long-term scenario analysis.



It is used to estimate future energy demand for a defined geographical area in different sectors such as:

* industry
* households
* traffic
* commerce, trade and services



The model can generate:

* Useful Energy
* Final Energy
* subregional yearly results
* temporally resolved results (hourly time series)



This allows the user to analyse not only total future demand, but also its sectoral, spatial, and temporal structure. Depending on the selected configuration, the model can represent different technologies, energy carriers, useful energy types, and temperature levels. It can therefore be used both for high-level scenario comparisons and for more detailed analyses of sectoral demand development, subregional distributions, and hourly load patterns.





### 2\. HOW TO INSTALL





If you only want to use the model, download the latest release from the repository and extract it.



We recommend using Conda or Mamba with Python 3.10.



Create the environment from the provided environment file:



conda env create -f endemo-env.yml

conda activate endemo



If needed, install additional packages manually.



Run the model



After installation, start the model from the project directory:



python main.py



The generated results are written to the output folder.

### 

### 3\. MODEL STRUCTURE AND LOGIC



#### 3.1 Main concept



The model follows the chain:

Demand Drivers -> ECU / DDet -> Useful Energy -> Final Energy



**DDr (Demand Drivers)**

Upstream explanatory variables such as population, GDP, employment, or time.



**ECU (Energy Consuming Units)**

Depending on the sector, an acting energy consumer or an energy consuming product.



**DDet (Demand Determinants)**

Factors which directly contribute to the level and structure of the energy consumption of an ECU.



**UE (Useful Energy)**

Calculated from ECU and DDet.



**FE (Final Energy)**

Derived from Useful Energy using efficiencies and energy carrier shares.



#### 3.2 Inputs



The model is based on four central Excel input files:

* Model\_Settings.xlsx
* Data\_yearly\_Hist.xlsx
* Data\_yearly\_Scenario\_<Scenario>.xlsx
* Data\_hourly.xlsx



##### Settings



Model\_Settings.xlsx defines the active model structure, including:

* active regions
* active sectors and subsectors
* ECU and DDet variables per subsector
* useful energy types
* heat levels
* final energy types
* selected scenario <Scenario>
* enabled outputs such as FE, subregions, and timeseries



Only variables and structural paths referenced in the settings are processed.



##### Yearly input data



The yearly input data are split into two files:

* Data\_yearly\_Hist.xlsx
* Data\_yearly\_Scenario\_<Scenario>.xlsx



Data\_yearly\_Hist.xlsx contains the historical input values used as the observed data basis of the model. These include historical time series for sectoral variables, demand drivers, and subregional distribution variables.



Data\_yearly\_Scenario\_<Scenario>.xlsx contains the scenario-specific input values and forecast definitions. This file defines how variables are extended into the future, for example through direct yearly values, historical forecasts, user-defined forecasts, interpolation points, or custom equations.



Each row describes one variable in one specific model context.



##### Meaning of abbreviations



* **Subsector**: Defines the more specific subdivision of a sector, for example a particular industrial branch or application group within a main sector.
* **Technology**: Specifies the technology option or process to which a variable applies, for example a specific heating technology.
* **Variable**: Defines the actual model variable represented by the row, for example an activity level, a specific demand value, or a share.
* **UE\_Type:** Specifies the useful energy type of the variable, for example electricity, heat, or mobility-related useful energy.
* **FE\_Type:** Specifies the final energy carrier associated with the variable, for example electricity, hydrogen, or fuel.
* **Temp\_level (heat levels):** Defines the temperature level of a heat-related variable and is used to distinguish between different heat demand classes.
* **Forecast data (user or historical):** Defines whether the future values are based on historical calibration or directly specified by the user in the scenario file.
* **Function**: Specifies the forecast method used to calculate future values, for example linear functions, interpolation, or custom equations.
* **Equation**: Contains the mathematical expression used for user-defined forecast functions.
* **Factor**: Applies a scaling factor to the calculated forecast values after the forecast itself has been computed.
* **Lower limit**: Defines the minimum allowed value for the forecasted variable before scaling is applied.
* **Upper limit:** Defines the maximum allowed value for the forecasted variable before scaling is applied.
* **k0, k1, …:** Define the coefficients of the selected forecast function, for example intercepts or slope parameters in linear or user-defined equations.



##### Hourly input data



Data\_hourly.xlsx contains load profiles used to distribute yearly results into hourly time series.



Profiles are matched by metadata such as:

* region
* sector
* subsector
* technology
* UE\_Type
* Temp\_level

#### 

#### 3.2 MODEL LOGIC



###### Forecast logic



Forecasts are defined row-wise and use a shared infrastructure for:

* ECU
* DDet
* dependent demand drivers
* subregional distribution variables



Two forecast modes are supported:



**Historical**

Function and dependencies come from the scenario file. Coefficients are estimated from historical data.



**User**

Coefficients, yearly values, interpolation points, or custom equations are taken directly from the scenario file.



###### Matching and merge logic



The model uses an exact-first, default-as-fallback principle.



Default rows are only used if no sufficiently specific row exists.



For yearly variables, matching is resolved from the variable level to the more detailed hierarchy, for example:

Variable -> Sector -> Subsector -> Technology -> further metadata -> Region



Historical and scenario data are merged into one combined variable description before forecasting starts.



###### Outputs



Depending on the configuration, the model generates:



* sector forecast files such as predictions\_<sector>.xlsx
* yearly useful energy files such as UE\_<sector>.xlsx
* yearly final energy files such as FE\_<sector>.xlsx
* demand driver outputs
* subregional outputs
* hourly timeseries outputs
* validation files
* optional trace information





### 4\. HOW TO CREATE YOUR OWN MODEL





To create your own model, proceed in five steps.



##### Step 1: Define the structure in the settings



In Model\_Settings.xlsx, add/activate:

* the regions you want to model
* the sectors and subsectors you want to include
* the ECU and DDet variables used in each subsector
* useful energy and final energy types
* optional subregional and timeseries outputs



The settings define the active model hierarchy. Only regions, sectors, subsectors, and variable paths referenced here are processed later in the model run.



If a new sector is added, a corresponding sheet for its subsectors must also be defined in the settings structure.



If subregional resolution is enabled, subregions must be defined for each active region. Missing or inconsistent subregional definitions can stop the model run.



##### Step 2: Add scenario and forecast definitions



In Data\_yearly\_Scenario\_<Scenario>.xlsx, define how each variable should behave in the future. This is the central modelling step, because the scenario file specifies the transition from historical input data to future model values.



The scenario file determines whether a variable is continued from historical patterns, prescribed directly by the user, or calculated from scenario assumptions. In this way, it contains the forecast logic of the model and controls the future development of ECU, DDet, demand drivers, and subregional distribution variables.



Typical options are:

* direct yearly values
* historical forecast
* user-defined forecast
* interpolation
* custom equation



The selected function then determines the mathematical form of the forecast, for example a simple continuation, a coefficient-based function, an interpolation, or a user-defined equation.



##### Step 3: Add historical input data (optional)



In Data\_yearly\_Hist.xlsx, add the historical rows for:

\- sectoral ECU and DDet variables

\- demand drivers

\- subregional distribution variables



Historical data is only required if variables should be calibrated or extended on the basis of observed past values.



A row is only processed correctly if both the variable name and the full metadata context match the settings and the historical data.



##### Step 4: Add hourly profiles (optional)



If hourly timeseries are enabled, add matching load profiles to Data\_hourly.xlsx.



The profiles define how yearly values are distributed over time. To be applied correctly, their metadata must match the corresponding model context, for example by region, sector, subsector, technology, UE\_Type, and Temp\_level.



##### Step 5: Run and validate



Run:

python main.py



Then check the generated outputs in the output folder.



**Important notes**



A variable row alone is not sufficient. The variable must also be referenced in the correct settings path.

Historical forecasts require overlapping numeric years for the target variable and all required demand drivers.

Missing or inconsistent subregional definitions can stop the run.

Timeseries together with subregional resolution can significantly increase runtime.





### 5\. LICENSE, DATASET AND COPYRIGHT





##### License



Please see the LICENSE file of this repository for the software license.



##### Dataset



The model historical input data used in the ENDEMO context are provided separately via the corresponding Zenodo dataset.

https://zenodo.org/records/17805753





### 6\. CITATIONS



Software

Kerekes, A., Breuning, L., Epishev, A., Kobalt, C. and Haag, M. endemo: Energy demand modeling tool. GitHub repository.



Dataset

Kerekes, A., Breuning, L., and Hamacher, T. ENDEMO-Europe: Dataset for European long-term cross-sectoral energy demand modelling. Zenodo.



Methodological reference

Kerekes, A., Breuning, L., Kuhn, P., and Hamacher, T. endemo – an Open-Source Energy Demand Modelling Framework in European Context.

See https://ssrn.com/abstract=4803430

