from django.contrib import admin
from .models import Wallet, WalletTransaction, Deposit, Withdrawal, Payout

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'available_balance', 'pending_balance', 'currency', 'is_frozen')
    list_filter = ('currency', 'is_frozen')
    search_fields = ('user__email', 'user__username', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'currency', 'created_at')
    search_fields = ('wallet__user__email', 'reference_id', 'description')
    readonly_fields = ('created_at', 'completed_at')
    raw_id_fields = ('wallet', 'related_ticket_sale')
    ordering = ('-created_at',)

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'amount', 'currency', 'deposit_method', 'status', 'created_at')
    list_filter = ('deposit_method', 'status', 'currency', 'created_at')
    search_fields = ('wallet__user__email', 'transaction_id')
    readonly_fields = ('created_at', 'completed_at')
    raw_id_fields = ('wallet', 'payment_method')
    ordering = ('-created_at',)

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'requested_amount', 'net_amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'withdrawal_speed', 'currency', 'created_at')
    search_fields = ('wallet__user__email', 'transaction_id', 'destination_identifier')
    readonly_fields = ('created_at', 'completed_at')
    raw_id_fields = ('wallet', 'requested_by', 'processed_by')
    ordering = ('-created_at',)

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'amount', 'currency', 'status', 'payout_period_start', 'payout_period_end', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('wallet__user__email', 'transaction_id', 'destination_identifier')
    readonly_fields = ('created_at', 'completed_at')
    raw_id_fields = ('wallet',)
    ordering = ('-created_at',)
