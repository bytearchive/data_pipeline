# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import sys

import mock
import pytest
from kazoo.client import KazooClient
from kazoo.exceptions import LockTimeout

from data_pipeline.zookeeper import ZK
from data_pipeline.zookeeper import ZKLock


class TestZK(object):
    @property
    def fake_namespace(self):
        return "test_namespace"

    @property
    def fake_name(self):
        return "test_name"

    @pytest.fixture
    def zk_client(self):
        return mock.Mock(autospec=KazooClient)

    @pytest.yield_fixture
    def patch_zk(self, zk_client):
        with mock.patch.object(
            ZK,
            'get_kazoo_client',
            return_value=zk_client
        ) as mock_get_kazoo:
            yield mock_get_kazoo

    @pytest.fixture
    def mock_zk(self, patch_zk, zk_client):
        return ZK()

    def test_create_close(self, mock_zk, zk_client):
        assert not zk_client.stop.call_count
        mock_zk.close()
        self._check_zk(zk_client)

    def _check_zk(self, zk_client):
        assert zk_client.start.call_count == 1
        assert zk_client.stop.call_count == 1
        assert zk_client.close.call_count == 1

class TestZKLock(TestZK):
    @property
    def lock_path(self):
        return "/{} - {}".format(self.fake_name, self.fake_namespace)

    @pytest.fixture
    def bad_lock(self):
        bad_lock = mock.Mock()
        bad_lock.acquire = mock.Mock(side_effect=LockTimeout('Test exception'))
        return bad_lock

    @pytest.fixture
    def locked_zk_client(self, bad_lock):
        zk_client = mock.Mock(autospec=(KazooClient))
        zk_client.Lock = mock.Mock(return_value=bad_lock)
        return zk_client

    @pytest.yield_fixture
    def locked_patch_zk(self, locked_zk_client):
        with mock.patch.object(
            ZKLock,
            'get_kazoo_client',
            return_value=locked_zk_client
        ) as mock_get_kazoo:
            yield mock_get_kazoo

    @pytest.yield_fixture
    def patch_exit(self):
        with mock.patch.object(
            sys,
            'exit'
        ) as mock_exit:
            yield mock_exit

    @pytest.fixture
    def mock_zk(
        self,
        zk_client,
        patch_zk
    ):
        return ZKLock(self.fake_name, self.fake_namespace)

    @pytest.fixture
    def mock_locked_zk(
        self,
        locked_zk_client,
        locked_patch_zk,
        patch_exit
    ):
        return ZKLock(self.fake_name, self.fake_namespace)

    def test_setup_lock_and_close(
        self,
        mock_zk,
        zk_client
    ):
        mock_zk.close()
        self._check_zk(zk_client)

    def test_lock_exception(
        self,
        mock_locked_zk,
        locked_zk_client,
        bad_lock,
        patch_exit
    ):
        assert patch_exit.call_count == 1
        self._check_zk(locked_zk_client)

    def test_double_lock(
        self,
        patch_exit
    ):
        zk1 = ZKLock(self.fake_name, self.fake_namespace)
        assert patch_exit.call_count == 0
        zk2 = ZKLock(self.fake_name, self.fake_namespace)
        assert patch_exit.call_count == 1
        zk1.close()

    def _check_zk(self, zk_client):
        super(TestZKLock, self)._check_zk(zk_client)
        zk_client.Lock.assert_called_once_with(
            self.lock_path,
            self.fake_namespace
        )
