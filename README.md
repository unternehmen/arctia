## What is Arctia?
Arctia is a small game inspired by Dwarf Fortress and Rimworld.
I am writing Arctia for practice, for fun, and as a tribute to the
"automated villagers" city-building game genre.

Tux and his friends were surprised when a huge ice chunk drifted
into the nearby sea.  The chunk was so huge that some penguins packed
their bags and decided to stake out a piece of the chunk to live on.
The elders call this new land "Arctia", and you are leading a colony
of penguin settlers on this new territory.

## Controls
You can switch tools by clicking the menu buttons on the left.

To designate areas using tools, click on tiles within the world.

To scroll across the map, right-click and drag.

## Dependencies
You need Pygame and PyTMX in order to run the game.

These are the versions I test it with:

* Pygame 1.9.3
* PyTMX 3.21.3

Both of them can be installed thru Pip like so:

    pip install --user pygame==1.9.3
    pip install --user pytmx==3.21.3

## Testing
There are some tests to make sure that certain parts of the code
work correctly.  To run the tests, I use nose 1.3.7.  To install
nose, you can use this command:

    pip install --user nose==1.3.7

To run the tests, type the following:

    nosetests -v tests

## Running
Just run:

    python arctia.py

## Screenshots
![In this picture of the game, five penguin settlers are standing in a group together.](screen1.png)

![In this picture of the game, the penguins are digging holes into the mountain.](screen2.png)

![In this picture of the game, the penguins are still digging holes, but the focus of the image is on the ground to their south which is littered with rubble.](screen3.png)

## License
♡2017 by unternehmen.  Copying is an act of love.
Feel free to copy, remix, and share this work.
(No need to give credit!)
