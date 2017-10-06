from .moleskin import Moleskin
import shutil


def test():
    moleskin = Moleskin()
    moleskin.p('')

    moleskin.p('red', [0, 1])
    moleskin.red('red', [0, 1])
    moleskin.pprint([0, 1])


def test_file_output():
    import os, time
    try:
        shutil.rmtree("./test-logs")
    except:
        pass

    m = Moleskin(file="./test-logs/test_output.log")
    m.debug('this line')

    m.start()
    time.sleep(3)
    m.split()

    # create file again to test
    m = Moleskin(file="./test-logs/logs/test_output.log")
    m.pprint('test')  # pprint uses `stream` key argument instead.

    # create file again to test
    m = Moleskin(file="./test-logs/logs/logs/test_output.log")

    # create file again to test
    m = Moleskin(file="./test-logs/logs/logs/test_output.log")

    m.p('is this working?')
    m.green('This should be working!')
    m.red('not sure about this')

    log = open('./test-logs/logs/logs/test_output.log', "r")
    content = log.read()
    print([content])
    assert content == 'is this working?\n\x1b[32mThis should be working!' \
                      '\x1b[0m\n\x1b[31mnot sure about this\x1b[0m\n', 'lines are incorrect'
    # remove the test file again.
    shutil.rmtree("./test-logs")


def test_timing():
    M = Moleskin()

    @M.timeit
    def slow(n=100):
        import time
        for i in range(n):
            time.sleep(0.01)

    slow(10)


def test_diff():
    M = Moleskin(file='./test-logs/diff_log.log')

    M.diff('.')

    file = open('./test-logs/index.diff')
    diff = file.read()
    M.print(diff)
    shutil.rmtree("./test-logs")


def test_singleton_config():
    from .moleskin import moleskin as M

    M.config(file="./test-logs/test.log")
    M.print('something')
    shutil.rmtree("./test-logs")
