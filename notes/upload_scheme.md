Why don't we use a git-based upload scheme?

## how would a git-based upload scheme look like?

1. send base commit
2. save local patch

The problem is that there could be local files (like secretes) that are not supposed to show up on git. or there could be binary files that do not show up correctly in the patches. 

We don't want to force everyone to go through the git bottle neck.


## how would we implement this (if we decided to go with git)

1. shadow commit --all to remote repo
2. upload to remote repo
3. switch back to original.

I got something like this to work at some point. This is potentially a lot faster for larger repos. But I can't say slowness in upload speed is a good "feature" to help the programmer to keep repo size in mind.

On the other hand, slow upload speed in a coffee shop is immensely annoying.
