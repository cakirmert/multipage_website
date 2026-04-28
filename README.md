# Hello world

Ene mene muh und draus bist du. Draus bist du noch lange nicht, musst erst sagen wie alt du bist.

Wer, wie, was, wieso, weshalb, warum? – Wer nicht fragt bleibt dumm!


# Basic structure

The app.py is the main file. It includes all apps from the whole webpage. It has a routing function and describes the home, impressum, etc.
Inside the app.py file you can find all code required to generate the plots.



# How to run it ?

Check out  https://dash.plotly.com/tutorial . To launch the app, type into your terminal the command 
To run it locally type :**python app.py**

# Update

Now all is in one single app file app.py . The home and the subpages

# How to add a new app ?

You need to make the link to it in the 'home_layout' function. Then inccorpertae the path at the 'display_page' function. Then teh user can find the path and is able to navigate to the app.
Next one needs to design a new design function for the new page this is then called by the 'display_page' function. Call the function  'xxxx_layout' .
Inside this function one designs how the page looks like. Below we need the @app_callback and the plotting function for the interactive plot in the new app.


