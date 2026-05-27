"""
DRF Serializers for Wallets
"""

from rest_framework import serializers
from .models import Wallet, WalletTransaction, Deposit, Withdrawal, Payout


class WalletTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    transaction_status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'wallet', 'transaction_type', 'transaction_type_display',
            'status', 'transaction_status_display', 'amount', 'currency',
            'balance_after', 'reference_id', 'description',
            'created_at', 'completed_at'
        ]
        read_only_fields = fields


class DepositSerializer(serializers.ModelSerializer):
    deposit_method_display = serializers.CharField(source='get_deposit_method_display', read_only=True)
    deposit_status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Deposit
        fields = [
            'id', 'wallet', 'amount', 'currency', 'deposit_method',
            'deposit_method_display', 'status', 'deposit_status_display',
            'transaction_id', 'payment_method', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at', 'completed_at']


class WithdrawalSerializer(serializers.ModelSerializer):
    withdrawal_speed_display = serializers.CharField(source='get_withdrawal_speed_display', read_only=True)
    withdrawal_status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Withdrawal
        fields = [
            'id', 'wallet', 'requested_amount', 'currency', 'fee_amount', 'net_amount',
            'withdrawal_speed', 'withdrawal_speed_display', 'status', 'withdrawal_status_display',
            'destination_provider', 'destination_identifier', 'transaction_id',
            'requested_by', 'requested_by_name', 'processed_by', 'processed_by_name',
            'rejection_reason', 'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'net_amount', 'transaction_id', 'processed_by', 'processed_by_name',
            'rejection_reason', 'created_at', 'completed_at'
        ]


class PayoutSerializer(serializers.ModelSerializer):
    payout_status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payout
        fields = [
            'id', 'wallet', 'amount', 'currency', 'status', 'payout_status_display',
            'payout_period_start', 'payout_period_end', 'destination_provider',
            'destination_identifier', 'transaction_id', 'included_ticket_sales_count',
            'included_revenue', 'created_at', 'completed_at'
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    total_balance = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'available_balance', 'pending_balance', 'total_balance',
            'currency', 'currency_display', 'is_frozen', 'freeze_reason',
            'recent_transactions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_recent_transactions(self, obj):
        transactions = obj.transactions.all()[:10]
        return WalletTransactionSerializer(transactions, many=True).data
