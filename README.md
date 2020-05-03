# Repiece

By:

- Mathias Ham
- Morgan Patterson
- Adam Turk

![pretty little image](https://cdn.discordapp.com/attachments/667782524692332544/681668394382262272/Greenpaece.jpg)

---

## What does it do?

In theory, all you have to do is upload an image of a shredded document and be patient, and it will return an image of that same document reassambled in all of it's original informative glory.

However... There were some limitations we found along the way including:

- Matching the edges of letters against eachother doesn't work
- edge checking every strip of paper is very computationally heavy
- very contrasting backgrounds are required for it to function properly
- Would not work well in practice on small cross cut shreds

## How do I develop it

1. if you haven't already installed python3 and virtualenv, do that
on ubuntu:  
    ``` sudo apt-get install python3 python3-pip ```  
2. `pip3 install virtualenv`
3. `virtualenv -p python3.7 venv`
4. `./venv/bin/activate`
5. `pip3 install -r build/requirements.txt`
6. Fix all of our code

## Todo

- make the greatValueDispatcher actually be Infrastructure as code
- improve the algorithm
- figure out how to stick the keys in the website nicely/use cognito so I don't have to hardcode keys in
- slim it down to only use lambda without having to wait on ECS?
