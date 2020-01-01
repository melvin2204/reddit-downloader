# From https://gist.github.com/aubricus/f91fb55dc6ba5557fbab06119420dd6a

def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=90):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    print("'\r{a} |{b}| {c}{d} {e}".format(a=prefix,b=bar,c=percents,d="%",e=suffix), end="", flush=True)

    if iteration == total:
        print("")