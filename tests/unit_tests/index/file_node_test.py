# -*- coding: utf-8 -*-

import pytest
from bajoo.index.file_node import FileNode


class TestFileNode(object):

    def test_get_hashes_on_new_node(self):
        node = FileNode('node')
        assert node.get_hashes() == (None, None)

    def test_get_hashes_on_node_with_state_none(self):
        node = FileNode('node')
        node.state = None
        assert node.get_hashes() == (None, None)

    def test_get_hashes_on_node_with_existing_hash(self):
        node = FileNode('node')
        node.state = {'local_hash': '123456',
                      'remote_hash': '789012'}
        assert node.get_hashes() == ('123456', '789012')

    def test_set_hashes_on_new_node(self):
        node = FileNode('node')
        node.set_hashes('abc', 'def')
        assert node.state.get('local_hash') == 'abc'
        assert node.state.get('remote_hash') == 'def'

    def test_set_hashes_many_times(self):
        node = FileNode('node')
        node.set_hashes('abc', 'def')
        node.set_hashes('bcd', 'ef1')
        assert node.state.get('local_hash') == 'bcd'
        assert node.state.get('remote_hash') == 'ef1'

    def test_set_none_hashes(self):
        node = FileNode('node')
        node.set_hashes('abc', 'def')
        node.set_hashes(None, None)
        assert node.state is None

    def test_only_one_hash_raise_an_exception(self):
        node = FileNode('node')

        with pytest.raises(ValueError):
            node.set_hashes('abc', None)
        with pytest.raises(ValueError):
            node.set_hashes(None, 'def')
