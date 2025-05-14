# postprocessing
I have a lot of data to postprocess. This is a personal problem. I am not expecting this to solve anyone elses's problems, computational or otherwise. So don't come on here with your bullshit optimism. Take that to the real coders.

I will try to describe exhaustively the code I am sharing on here. Because I wasted about 3 months of my life rewriting a code using chatgpt which I had already written to perfection with  bleeding fingernails and a broken heart. So here goes.

1. readscolumns.py
    If you have an excel file with four columns with four headers titled **Voltage_Calib	Current_Calib	Voltage_Uncalib	Current_Uncalib** this program will go through each of the columns and give you the Pmax, Vmax and Imax for both datasets. It will also get you the short circuit current and Open circuit voltage. 


2. rcolumsfinderror.py
This one does what read columns does and then it takes one set of readings and uses it to interpolate for the second set. eg. it will take vcalibrated and Icalibrated and then find the interpolated values of current from the second dataset for the vcalibrated values. It will also print the error of the interpolated values and the values of the calibrated dataset

3. error.py
The code measures solar cells. It takes numbers from a file. Two kinds of numbers:
Good numbers (calibrated)
Rough numbers (uncalibrated)
First it cleans the good numbers. Cuts off bad parts where voltage drops too fast. Like trimming rotten wood from a board.
Then it finds important points:

 1. Pmax (where power is strongest)
2. Vmax, Imax (voltage and current at Pmax)
3. Isc (current with no voltage)
4. Voc (voltage with no current)

Simple. Clear.
Next it compares rough numbers to good numbers. Lines them up. Sees how close they are. The differences are errors. 
It checks errors in three places:
1. Near Pmax (most important)
2. Near Isc (where current runs free)
3. Near Voc (where current stops)

The code makes two pictures:
1. Shows the curves - good and rough
2. Shows the errors - where rough misses good

Finally it says the numbers. Mean error. Max error. By region. No decoration. Just facts. Good code. Does its job. Like a solid ax handle. No nonsense. You could trust it in the woods.

