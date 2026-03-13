# TODO

## Features

- [ ] web interface for less technical users. explains the details eloquently (hidden behind i button hovers), shows grace by allowing the user to change previous entries before final conf

## Bugs

- [x] can we add something to repo_new (and any other script this applies to) where if we are already logged into the gh account we need to be logged into that it wont log the user out? as it stands gh auth logout runs regardless. but i kinda want a pattern matching thing. my understanding is fuzzy here so help me out. but if a user is requesting to set up a new repo for xyz username and that username matches the result of gh auth status then dont log out. if no match then log out so we can log in with correct name. what is the most pythonic way to do that? be sure to scan the other scripts too i dont think this is the only place this logic can apply.
- [x] Very weird case that I do not understand: usernames, ssh login entry, and then the repo URL in existing are all some degree of case sensitive? as in, if some dont match sometimes the script will not detect which ssh pub key it is supposed to be matching... uses the wrong one. I dont even know how to define this well but we need to find the edge case, replicate the bug and add exhaustive tests once we figure out the work around.

## Improvements

- [x] Add logging that goes to ./data/logs/ 
- [ ] In the @main branch check ./trick.md, let's improve that process of path entry by using the trick
- [ ] Instead of --yes lets do --force, idk for sure but think force is more in line with typical pythonic convention for CLI tools
