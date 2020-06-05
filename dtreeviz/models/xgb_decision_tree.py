import json
import math
from collections import defaultdict
from typing import List, Mapping

import numpy as np
import xgboost as xgb
from xgboost.core import Booster

from dtreeviz.exceptions import VisualisationNotYetSupportedError
from dtreeviz.models.shadow_decision_tree import ShadowDecTree3


class XGBDTree(ShadowDecTree3):
    LEFT_CHILDREN_COLUMN = "Yes"
    RIGHT_CHILDREN_COLUMN = "No"
    NO_CHILDREN = -1
    NO_SPLIT = -2
    NO_FEATURE = -2
    ROOT_NODE = 0

    # TODO
    # do we need data as parameter ? should it be dataframe or dmetrics ?
    def __init__(self, booster: Booster,
                 tree_index: int,
                 x_data,
                 y_data,
                 feature_names: List[str] = None,
                 target_name: str = None,
                 class_names: (List[str], Mapping[int, str]) = None
                 ):
        self.booster = booster
        self.tree_index = tree_index
        self.tree_to_dataframe = self._get_tree_dataframe()
        self.children_left = self._calculate_children(self.__class__.LEFT_CHILDREN_COLUMN)
        self.children_right = self._calculate_children(self.__class__.RIGHT_CHILDREN_COLUMN)

        super().__init__(booster, x_data, y_data, feature_names, target_name, class_names)

    def is_fit(self):
        return isinstance(self.booster, Booster)

    # TODO - add implementation
    def get_class_weights(self):
        return None

    # TODO - add implementation
    def get_class_weight(self):
        return None

    def criterion(self):
        raise VisualisationNotYetSupportedError("criterion()", "XGBoost")

    def get_children_left(self):
        return self._calculate_children(self.__class__.LEFT_CHILDREN_COLUMN)

    def get_children_right(self):
        return self._calculate_children(self.__class__.RIGHT_CHILDREN_COLUMN)

    def get_node_split(self, id) -> (float):
        """
        Split values could not be the same like in plot_tree(booster). This is because xgb_model_classifier.joblib.trees_to_dataframe()
        get data using dump_format = text from xgb_model_classifier.joblib.get_dump()
        """
        node_split = self._get_column_value("Split")[id]
        return node_split if not math.isnan(node_split) else self.__class__.NO_SPLIT

    def get_node_feature(self, id) -> int:
        feature_name = self._get_column_value("Feature")[id]
        try:
            return self.booster.feature_names.index(feature_name)
        except ValueError as error:
            return self.__class__.NO_FEATURE

    def get_features(self):
        feature_index = [self.get_node_feature(i) for i in range(0, self.nnodes())]
        return np.array(feature_index)

    def get_node_samples(self):
        """
        Return dictionary mapping node id to list of sample indexes considered by
        the feature/split decision.
        """
        # Doc say: "Return a node indicator matrix where non zero elements
        #           indicates that the samples goes through the nodes."

        prediction_leaves = self.booster.predict(xgb.DMatrix(self.x_data, feature_names=self.feature_names),
                                                 pred_leaf=True)[:, self.tree_index]
        node_to_samples = defaultdict(list)
        for sample_i, prediction_leaf in enumerate(prediction_leaves):
            prediction_path = self._get_leaf_prediction_path(prediction_leaf)
            for node_id in prediction_path:
                node_to_samples[node_id].append(sample_i)

        return node_to_samples

    def _get_leaf_prediction_path(self, leaf):
        prediction_path = [leaf]

        def walk(node_id):
            if node_id != self.__class__.ROOT_NODE:
                try:
                    parent_node = np.where(self.children_left == node_id)[0][0]
                    prediction_path.append(parent_node)
                    walk(parent_node)
                except IndexError:
                    pass

                try:
                    parent_node = np.where(self.children_right == node_id)[0][0]
                    prediction_path.append(parent_node)
                    walk(parent_node)
                except IndexError:
                    pass

        walk(leaf)
        return prediction_path

    def _get_tree_dataframe(self):
        return self.booster.trees_to_dataframe().query(f"Tree == {self.tree_index}")

    def _get_column_value(self, column_name):
        return self._get_tree_dataframe()[column_name].to_numpy()

    def _split_column_value(self, column_name):
        def split_value(value):
            if isinstance(value, str):
                return value.split("-")[1]
            else:
                return value

        return self.tree_to_dataframe.apply(lambda row: split_value(row.get(f"{column_name}")), axis=1)

    def _change_no_children_value(self, children):
        return children.fillna(self.__class__.NO_CHILDREN)

    def _calculate_children(self, column_name):
        children = self._split_column_value(column_name)
        children = self._change_no_children_value(children)
        return children.to_numpy(dtype=int)

    def get_feature_path_importance(self, node_list):
        raise VisualisationNotYetSupportedError("get_feature_path_importance()", "XGBoost")

    def get_node_criterion(self):
        raise VisualisationNotYetSupportedError("get_node_criterion()", "XGBoost")

    def get_thresholds(self):
        thresholds = [self.get_node_split(i) for i in range(0, self.nnodes())]
        return np.array(thresholds)

    # TODO
    # - find a better name
    def get_value(self, id):
        all_nodes = self.internal + self.leaves
        node_value = [node.n_sample_classes() for node in all_nodes if node.id == id]
        return node_value[0][0], node_value[0][1]

    # TODO - add implementation
    def is_classifier(self):
        config = json.loads(self.tree_model.save_config())
        objective_name = config["learner"]["objective"]["name"].split(":")[0]
        if objective_name == "binary":
            return True
        elif objective_name == "reg":
            return False
        return None

    def nnodes(self):
        return self.tree_to_dataframe.shape[0]

    def nclasses(self):
        return len(np.unique(self.y_data))

    def classes(self):
        return np.unique(self.y_data)

    def get_max_depth(self):
        raise VisualisationNotYetSupportedError("get_max_depth()", "XGBoost")

    def get_score(self):
        raise VisualisationNotYetSupportedError("get_score()", "XGBoost")

    def get_min_samples_leaf(self):
        raise VisualisationNotYetSupportedError("get_min_samples_leaf()", "XGBoost")
