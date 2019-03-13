# rapLyrics
"Source code" for this video: https://www.youtube.com/watch?v=a0EyfdQ0QTQ

The real machine learning code is Andrej Karpathy's here: https://github.com/karpathy/char-rnn

I'm only adding 2 files here bc I didn't actually code that much.

"rapSpeaker.py" was used to convert text files to spoken audio files. It's super specific to my uses, so it might not be adaptable to what you'd want to use, but you can take a look!

"multiRapper.py" is what I used to create a text sampling of each 2-second checkpoint of Andrej's RNN code. It finds all files from the checkpoint file and uses them, in chronological order, for the sampling.
