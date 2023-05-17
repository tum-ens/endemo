# endemo2
Rework of an Useful Energy Demand Model

## Class Specification
### Timeseries

Contains historical data and provides methods for making predictions based on it

|  			**Attributes** 		  |                                                                                                                                |
|---------------|--------------------------------------------------------------------------------------------------------------------------------|
|  			Name 		        |  			data 		                                                                                                                         |
|  			Type 		        |  			List 			of 2D points 		                                                                                                            |
|  			Description 		 |  			encapsulates 			the historically available data for the timeseries 		                                                              |
|               |                                                                                                                                |
|  			Name 		        |  			coefficients 		                                                                                                                 |
|  			Type 		        |  			(const(k0), 			lin(k0, k1), quadr(k0, k1, k2)) 		                                                                                  |
|  			Description 		 |  			used 			to save the coefficients of data, calculated by constant 			extrapolation, linear regression or quadratic regression 		       |
|               |                                                                                                                                |
|  			**Methods** 		     |                                                                                                                                |
|  			Name 		        |  			calc_coef_const 		                                                                                                              |
|  			Parameter 		   |  			rate 			of change 		                                                                                                               |
|  			Returns 		     |  			the 			calculated coefficient for the data, when using a constant change 			rate 		                                                   |
|               |                                                                                                                                |
|  			Name 		        |  			calc_coef_lin 		                                                                                                                |
|  			Parameter 		   |  			- 		                                                                                                                            |
|  			Returns 		     |  			the 			calculated coefficients for the data, when using linear regression 		                                                       |
|               |                                                                                                                                |
|  			Name 		        |  			calc_coef_quadr 		                                                                                                              |
|  			Parameter 		   |  			- 		                                                                                                                            |
|  			Returns 		     |  			the 			calculated coefficients for the data, when using a quadratic 			regression 		                                                  |
|               |                                                                                                                                |
|  			Name 		        |  			get_data 		                                                                                                                     |
|  			Parameter 		   |  			x 			axis value 		                                                                                                                 |
|  			Returns 		     |  			the 			corresponding y axis value of historical data 		                                                                            |
|               |                                                                                                                                |
|  			Name 		        |  			get_prog_lin 		                                                                                                                 |
|  			Parameter 		   |  			x 			axis value 		                                                                                                                 |
|  			Returns 		     |  			the 			predicted y axis value, calculated by the usage of linear 			regression 		                                                     |
|               |                                                                                                                                |
|  			Name 		        |  			get_prog_quadr 		                                                                                                               |
|  			Parameter 		   |  			x axis value 		                                                                                                                 |
|  			Returns 		     |  			the predicted y axis value, calculated by the usage of quadratic 			regression 		                                                  |
|  			   			 		         |                                                                                                                                |
|  			Name 		        |  			get_prog_const_mean 		                                                                                                          |
|  			Parameter 		   |  			x axis value 		                                                                                                                 |
|  			Returns 		     |  			the predicted y axis value, calculated by a constant change rate, 			with the start value being the mean of the historical data 		 |

### PredictedTimeseries (derived from Timeseries)

A special case of Timeseries, where there already is a manual prediction (population for example)

|  			**Attributes** 		  |                                                        |
|---------------|--------------------------------------------------------|
|  			Name 		        |  			prediction 		                                           |
|  			Type 		        |  			List of 2D points 		                                    |
|  			Description 		 |  			the manually created prediction 		                      |
|               |                                                        |
|  			**Methods** 		     |                                                        |
|  			Name 		        |  			get_prognosis 		                                        |
|  			Parameter 		   |  			x axis value 		                                         |
|  			Returns 		     |  			the predicted y axis value, by the manual prediction 		 |

### TimeStepSequence

Used when the prediction is defined by ranges and percent increases in those ranges

|  			**Attributes** 		  |                                                                                                                     |
|---------------|---------------------------------------------------------------------------------------------------------------------|
|  			Name 		        |  			start_value 		                                                                                                       |
|  			Type 		        |  			2D 			point 		                                                                                                          |
|  			Description 		 |  			the 			base value, predictions use as a starting point 		                                                               |
|               |  			   			 		                                                                                                               |
|  			Name 		        |  			progression 		                                                                                                       |
|  			Type 		        |  			List of time intervals with their corresponding rate of change 		                                                    |
|  			Description 		 |  			- 		                                                                                                                 |
|               |                                                                                                                     |
|  			**Methods** 		     |                                                                                                                     |
|  			Name 		        |  			get_prognosis 		                                                                                                     |
|  			Parameter 		   |  			x 			axis value 		                                                                                                      |
|  			Returns 		     |  			the predicted y axis value, calculated by use of the specified 			increases by intervals in the progression variable 		 |

### Product

An industrial product, per industry, per country
|  			**Attributes** 		  |                                                            |
|---------------|------------------------------------------------------------|
|  			Name 		        |  			specific_consumption 		                                     |
|  			Type 		        |  			(energy, electricity, heat, hydrogen, max_subst_heat_h2) 		 |
|  			Description 		 |  			- 		                                                        |
|               |  			   			 		                                                      |
|  			Name 		        |  			bat 		                                                      |
|  			Type 		        |  			(energy, electricity, heat) 		                              |
|  			Description 		 |  			- 		                                                        |
|               |                                                            |
|  			**Methods** 		     |                                                            |
|  			Name 		        |  			calculate_demand 		                                         |
|  			Parameter 		   |  			year 			to be calculated 		                                    |
|  			Returns 		     |  			the demand as a namedtuple(electricity, heat, hydrogen) 		  |

### ProductHistorical (derived from Product)

A product, which has been produced in the past and has historical data available.

|  			**Attributes** 		  |                                                                                                                           |
|---------------|---------------------------------------------------------------------------------------------------------------------------|
|  			Name 		        |  			amount_per_year 		                                                                                                         |
|  			Type 		        |  			Timeseries 		                                                                                                              |
|  			Description 		 |  			the 			timeseries containing the absolute amount produced from this 			product on the y axis and the year on the x axis 		       |
|               |  			   			 		                                                                                                                     |
|  			Name 		        |  			amount_per_gdp 		                                                                                                          |
|  			Type 		        |  			Timeseries 		                                                                                                              |
|  			Description 		 |  			the 			timeseries containing the absolute amount produced from this 			product on the y axis and the gdp on the x axis 		        |
|               |  			   			 		                                                                                                                     |
|  			Name 		        |  			rel_amount_per_year 		                                                                                                     |
|  			Type 		        |  			Timeseries 		                                                                                                              |
|  			Description 		 |  			the 			timeseries containing the amount per population produced from this 			product on the y axis and the year on the x axis 		 |
|               |  			   			 		                                                                                                                     |
|  			Name 		        |  			rel_amount_per_gdp 		                                                                                                      |
|  			Type 		        |  			Timeseries 		                                                                                                              |
|  			Description 		 |  			the 			timeseries containing the amount per population produced from this 			product on the y axis and the gdp on the x axis 		  |

### ProductFutureTech (derived from Product)

This product method has no historical data, but a number indicating the percentage of usage for a product.

|  			**Attributes** 		  |                                                                         |
|---------------|-------------------------------------------------------------------------|
|  			Name 		        |  			per_renew 		                                                             |
|  			Type 		        |  			float 		                                                                 |
|  			Description 		 |  			the 			percentage of the product being produced by this renewable method 		 |
|               |  			   			 		                                                                   |
|  			Name 		        |  			historical_counterpart 		                                                |
|  			Type 		        |  			ProductHistorical 		                                                     |
|  			Description 		 |  			the 			associated product, which has historical data available 		           |

### Sector

Can be industry, household, commercial trades and services or transport.

|  			**Attributes** 		  |                                                                    |
|---------------|--------------------------------------------------------------------|
|  			Name 		        |  			input_path 		                                                       |
|  			Type 		        |  			a pathlib Path object 		                                            |
|  			Description 		 |  			the path to the folder containing the input files for the sector 		 |
|               |                                                                    |
|  			**Methods** 		     |                                                                    |
|  			Name 		        |  			calculate_demand 		                                                 |
|  			Parameter 		   |  			the year, demand should be calculated for 		                        |
|  			Returns 		     |  			the calculated demand of the whole sector for a certain year 		     |

### Industry (derived from Sector)

Industry per country

|  			**Attributes** 		  |                                                                    |
|---------------|--------------------------------------------------------------------|
|  			Name 		        |  			products 		                                                         |
|  			Type 		        |  			a pathlib Path object 		                                            |
|  			Description 		 |  			the path to the folder containing the input files for the sector 		 |
|               |                                                                    |
|  			**Methods** 		     |                                                                    |
|  			Name 		        |  			calculate_demand 			(overwritten) 		                                   |
|  			Parameter 		   |  			the year, demand should be calculated for 		                        |
|  			Returns 		     |  			The sum of “calculate_demand” on each product 		                    |

### Country

A country to calculate demand for.

|  			**Attributes** 		  |                                                               |
|---------------|---------------------------------------------------------------|
|  			Name 		        |  			name 		                                                        |
|  			Type 		        |  			string 		                                                      |
|  			Description 		 |  			name 			of the country 		                                         |
|               |                                                               |
|  			Name 		        |  			abbreviations 		                                               |
|  			Type 		        |  			List 			of strings 		                                             |
|  			Description 		 |  			possible 			other names for the country 		                        |
|               |                                                               |
|  			Name 		        |  			population 		                                                  |
|  			Type 		        |  			PredictedTimeseries 		                                         |
|  			Description 		 |  			the 			historical population with their manual predictions 		     |
|               |                                                               |
|  			Name 		        |  			gdp 		                                                         |
|  			Type 		        |  			TimeStepSequence 		                                            |
|  			Description 		 |  			the 			historical gdp combined with its manual prediction data 		 |
|               |                                                               |
|  			Name 		        |  			sectors 		                                                     |
|  			Type 		        |  			dictionary(sector 			name, Sector object) 		                      |
|  			Description 		 |  			holds 			all the different sectors for a country 		               |
|               |                                                               |
|  			**Methods** 		     |                                                               |
|  			Name 		        |  			calculate_demand 		                                            |
|  			Parameter 		   |  			year 			to calculate demand for 		                                |
|  			Returns 		     |  			the 			demand of all sectors combined 		                          |

### CountryGroup (in progress)

Used to group countries and do combined calculations

|  			**Attributes** 		  |                                                                     |
|---------------|---------------------------------------------------------------------|
|  			Name 		        |  			group 		                                                             |
|  			Type 		        |  			List of Country 		                                                   |
|  			Description 		 |  			all Countries that are within this group 		                          |
|               |                                                                     |
|  			Name 		        |  			comb_type 		                                                         |
|  			Type 		        |  			enum{joined, joined_separate} 		                                     |
|  			Description 		 |  			defined, how the countries should be combined in the calculation 		  |
|               |                                                                     |
|  			**Methods** 		     |                                                                     |
|  			Name 		        |  			quadratic_regression_multiple 		                                     |
|  			Parameter 		   |  			- 		                                                                 |
|  			Returns 		     |  			The calculated coefficients for the group and the country offsets 		 |

### CountryChecker

Tool to check if a string exists as a certain country and also check whole lists of strings

|  			**Attributes** 		  |                                                                                                      |
|---------------|------------------------------------------------------------------------------------------------------|
|  			Name 		        |  			valid_country_names 		                                                                                |
|  			Type 		        |  			set 			of strings 		                                                                                     |
|  			Description 		 |  			the 			names that are recognized as countries 		                                                         |
|  			   			 		         |  			   			 		                                                                                                |
|  			**Methods** 		     |                                                                                                      |
|  			Name 		        |  			is_country_valid 		                                                                                   |
|  			Parameter 		   |  			name 			of a country 		                                                                                  |
|  			Returns 		     |  			true 			iff. the country is contained in valid_country_names 		                                          |
|  			   			 		         |  			   			 		                                                                                                |
|  			Name 		        |  			is_country_list_valid 		                                                                              |
|  			Parameter 		   |  			List 			of country names 		                                                                              |
|  			Returns 		     |  			true 			iff. all countries in the list are valid according to 			is_country_valid 		                        |
|  			   			 		         |  			   			 		                                                                                                |
|  			Name 		        |  			check_for_wrong_countries_in_file 		                                                                  |
|  			Parameter 		   |  			The 			files name and a list of countries 		                                                             |
|  			Returns 		     |  			Result 			of is_country_list_valid and gives warnings with file name and 			lists unknown countrie names 		 |
