__author__ = 'linas'
'''
Shows how to execute a remote model building.
'''
import testfm
import pandas as pd
from testfm.evaluation.evaluator import Evaluator
from testfm.models.baseline_model import Popularity, RandomModel
from testfm.okapi.connector import PopularityOkapi, BPROkapi
from pkg_resources import resource_filename

#prepare the data
df = pd.read_csv(resource_filename(testfm.__name__,'data/movielenshead.dat'),
    sep="::", header=None, names=['user', 'item', 'rating', 'date', 'title'])
print df.head()

#tell me what models we want to evaluate
models = [
            RandomModel(),
            PopularityOkapi(host='54.72.18.118',
                            username='hadoop',
                            #okapi_jar_dir='/Users/linas/devel/okapi/target/',
                            #okapi_jar_base_name='okapi-0.3.2-SNAPSHOT-jar-with-dependencies.jar',
                            public_key_path='/Users/linas/.ssh/hack-okapi.pem'
            ),
            Popularity(normalize=False),
            BPROkapi(host='54.72.18.118',
                            username='hadoop',
                            #okapi_jar_dir='/Users/linas/devel/okapi/target/',
                            #okapi_jar_base_name='okapi-0.3.2-SNAPSHOT-jar-with-dependencies.jar',
                            public_key_path='/Users/linas/.ssh/hack-okapi.pem'
            )
]

#setup the environment
evaluator = Evaluator()

for m in models:
    m.fit(df)
    print m.getName().ljust(50),
    print evaluator.evaluate_model(m, df)

evaluator.close()#need this call to clean up the worker processes
