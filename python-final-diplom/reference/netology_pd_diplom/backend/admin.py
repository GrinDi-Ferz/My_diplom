from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken

# Inline-редакторы
class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    fields = ('product', 'external_id', 'model', 'quantity', 'price', 'price_rrc', 'shop')
    extra = 0


class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    fields = ('parameter', 'value')
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product_info', 'quantity')
    extra = 0


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'type', 'is_staff', 'is_active'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'type','is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    filter_horizontal = ('shops',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)
    list_filter = ('category',)
    inlines = [ProductInfoInline, ProductParameterInline]


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('product', 'shop', 'external_id', 'quantity', 'price', 'price_rrc')
    list_filter = ('shop', 'product')
    search_fields = ('product__name', 'shop__name', 'external_id')
    raw_id_fields = ('product', 'shop')


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('name',)



@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ('product_info', 'parameter', 'value')
    raw_id_fields = ('product_info', 'parameter')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    pass


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    pass


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    pass


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at',)
