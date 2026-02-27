"""
Mock AWS Glue modules for local testing
"""

class DynamicFrame:
    """Mock DynamicFrame for testing"""
    def __init__(self, df, glue_context, name):
        self._df = df
        self._glue_context = glue_context
        self._name = name
    
    def toDF(self):
        """Convert to Spark DataFrame"""
        return self._df
    
    def count(self):
        """Count records"""
        return self._df.count()
    
    @staticmethod
    def fromDF(df, glue_context, name):
        """Create DynamicFrame from DataFrame"""
        return DynamicFrame(df, glue_context, name)
