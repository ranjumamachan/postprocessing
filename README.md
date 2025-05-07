# postprocessing
I have a lot of data to postprocess. This is a personal problem. I am not expecting this to solve anyone elses's problems, computational or otherwise. So don't come on here with your bullshit optimism. Take that to the real coders.

I will try to describe exhaustively the code I am sharing on here. Because I wasted about 3 months of my life rewriting a code using chatgpt which I had already written to perfection with  bleeding fingernails and a broken heart. So here goes.

1. readscolumns.py
    If you have an excel file with four columns with four headers titled **Voltage_Calib	Current_Calib	Voltage_Uncalib	Current_Uncalib** this program will go through each of the columns and give you the Pmax, Vmax and Imax for both datasets. It will also get you the short circuit current and Open circuit voltage. 


2. rcolumsfinderror.py
This one does what read columns does and then it takes one set of readings and uses it to interpolate for the second set. eg. it will take vcalibrated and Icalibrated and then find the interpolated values of current from the second dataset for the vcalibrated values. It will also print the error of the interpolated values and the values of the calibrated dataset

